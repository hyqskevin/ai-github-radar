"""TDD tests for scripts/audit-loop.py.

策略：把 audit-loop.py 当黑盒，构造不同项目根状态，subprocess 调起脚本，
断言退出码 + stdout 关键字 + JSON 结构。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "audit-loop.py"


def _run_audit(
    project_root: Path,
    *args: str,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """在 project_root 里跑 audit-loop.py,捕获 stdout/stderr。"""
    cmd = [sys.executable, str(SCRIPT), *args]
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(project_root / "fake-home"),
        "PYTHONPATH": str(REPO_ROOT / "backend"),
    }
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        cmd,
        cwd=project_root,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


@pytest.fixture()
def fake_repo(tmp_path: Path) -> Path:
    """构造一个最小合规仓库用于 audit-loop 校验。"""
    _seed_required_docs(tmp_path)
    # TODO.md 含 1 条已完成 + 1 条未完成,且引用的 spec 都存在
    (tmp_path / "docs" / "TODO.md").write_text(
        "# TODO\n\n- [x] **T999** — done\n  - spec: docs/superpowers/specs/exists.md\n"
        "- [ ] **T1000** — pending\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "superpowers" / "specs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "superpowers" / "specs" / "exists.md").write_text(
        "# exists spec\n", encoding="utf-8"
    )
    # git init + 一个合规 commit
    _git_init_with_commit(tmp_path, "TODO(999): add fixture\n")
    return tmp_path


def _seed_required_docs(tmp_path: Path) -> None:
    """在 tmp_path 下种 A 类 8 必填文档。"""
    (tmp_path / "SPEC.md").write_text("# SPEC\n", encoding="utf-8")
    (tmp_path / "docs").mkdir(exist_ok=True)
    for name in (
        "api-doc.md",
        "database-design.md",
        "ui-design.md",
        "architecture.md",
        "phase-roadmap.md",
        "observability.md",
        "deployment.md",
    ):
        (tmp_path / "docs" / name).write_text(f"# {name}\n", encoding="utf-8")


def _git_init_with_commit(tmp_path: Path, msg: str) -> None:
    """git init + 全 add + commit msg(用于 L2 测试)。"""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", msg], cwd=tmp_path, check=True)


def test_ac1_fake_clean_repo_passes(fake_repo: Path) -> None:
    """AC-1: 合规仓库(默认非 strict) 退出码 0。"""
    # fake_repo 已合规,audit 应该全 ok / warn
    result = _run_audit(fake_repo)
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert "[L0] OK" in result.stdout
    assert "[L7] OK" in result.stdout
    assert "[L8] OK" in result.stdout


def test_ac2_l0_detects_missing_required_doc(tmp_path: Path) -> None:
    """AC-2: 删掉 SPEC.md,L0 报 ERROR。"""
    _seed_required_docs(tmp_path)
    (tmp_path / "SPEC.md").unlink()
    result = _run_audit(tmp_path, "--strict")
    assert "[L0]" in result.stdout
    assert "ERROR" in result.stdout
    assert "SPEC.md" in result.stdout


def test_ac3_l1_detects_missing_spec_reference(tmp_path: Path) -> None:
    """AC-3: TODO.md 引用不存在的 spec,L1 报 ERROR。"""
    _seed_required_docs(tmp_path)
    (tmp_path / "docs" / "TODO.md").write_text(
        "- [x] **T001** — x\n  - spec: docs/superpowers/specs/does-not-exist.md\n",
        encoding="utf-8",
    )
    result = _run_audit(tmp_path, "--strict")
    assert "[L1]" in result.stdout
    assert "ERROR" in result.stdout
    assert "does-not-exist" in result.stdout


def test_ac4_l4_detects_missing_happy_path_test(tmp_path: Path) -> None:
    """AC-4: 写的 TODO 引用不存在的 src → audit 跳过(not enforced)。

    真实场景(L4): src 存在但 test 不存在。L4 用 _guess_src_for_todo + _guess_test_path,
    我们建一个 src + TODO,但不创建对应 test,期望 L4 报错。
    """
    _seed_required_docs(tmp_path)
    # 用真实不存在的 src 路径(避免推断到已有 test)
    (tmp_path / "backend" / "ai_github_radar" / "fakemod").mkdir(parents=True)
    (tmp_path / "backend" / "ai_github_radar" / "fakemod" / "foo.py").write_text(
        "# ok\n", encoding="utf-8"
    )
    (tmp_path / "docs" / "TODO.md").write_text(
        "- [x] **T005** — sample `fakemod/foo.py`\n",
        encoding="utf-8",
    )
    _git_init_with_commit(tmp_path, "TODO(005): sample")
    result = _run_audit(tmp_path, "--strict")
    # test_audit_loop 推断 test 路径 → tests/unit/test_fakemod_foo.py → 不存在 → ERROR
    assert "[L4]" in result.stdout
    assert "ERROR" in result.stdout
    assert result.returncode == 1


def test_ac5_l7_detects_trae_path_breach(tmp_path: Path) -> None:
    """AC-5: .trae/ 下文件入侵,L7 报 ERROR。"""
    _seed_required_docs(tmp_path)
    (tmp_path / "docs" / "TODO.md").write_text("# TODO\n", encoding="utf-8")
    (tmp_path / ".trae").mkdir()
    (tmp_path / ".trae" / "spec.md").write_text("# rogue\n", encoding="utf-8")
    result = _run_audit(tmp_path, "--strict")
    assert "[L7]" in result.stdout
    assert "ERROR" in result.stdout
    assert ".trae" in result.stdout


def test_ac6_json_output_is_valid_json_with_required_keys(fake_repo: Path) -> None:
    """AC-6: --json 输出合法 JSON 且 6 个 level key。"""
    result = _run_audit(fake_repo, "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    for level in ("L0", "L1", "L2", "L4", "L7", "L8"):
        assert level in data


def test_ac7_level_filter_skips_other_levels(fake_repo: Path) -> None:
    """AC-7: --level L0 只跑 L0,stdout 不含 [L4]。"""
    result = _run_audit(fake_repo, "--level", "L0")
    assert "[L0]" in result.stdout
    assert "[L4]" not in result.stdout
    assert "[L7]" not in result.stdout


def test_ac8_l2_detects_commit_without_prefix(tmp_path: Path) -> None:
    """AC-8: 最近 commit 无 TODO(<id>): 前缀,L2 报 WARN(默认非阻断)。"""
    _seed_required_docs(tmp_path)
    _git_init_with_commit(tmp_path, "fix typo without prefix")
    result = _run_audit(tmp_path)  # 非 strict
    assert "[L2]" in result.stdout
    assert "WARN" in result.stdout
    assert result.returncode == 0  # WARN 默认不阻断


def test_c7_no_git_repo_l2_skipped(tmp_path: Path) -> None:
    """C7: 非 git 仓库,L2 跳过且不报 ERROR。"""
    _seed_required_docs(tmp_path)
    (tmp_path / "docs" / "TODO.md").write_text("# TODO\n", encoding="utf-8")
    result = _run_audit(tmp_path)
    assert "[L2]" in result.stdout
    assert "SKIP" in result.stdout
    assert result.returncode == 0


def test_c9_unknown_level_exits_with_error(tmp_path: Path) -> None:
    """C9: --level 含未知 level,argparse 报 error 退出码 2。"""
    result = _run_audit(tmp_path, "--level", "L99")
    assert result.returncode == 2


def test_c11_l2_accepts_non_numeric_id_prefix(tmp_path: Path) -> None:
    """C11: L2 接受 TODO(PRE-001) / TODO(INFRA) 等非数字 ID,不报 WARN。"""
    _seed_required_docs(tmp_path)
    _git_init_with_commit(tmp_path, "TODO(PRE-001): add scaffold\n")
    # 再加一个非数字 commit(用 touch 新文件再 add + commit)
    (tmp_path / "extra.md").write_text("# extra\n", encoding="utf-8")
    subprocess.run(["git", "add", "extra.md"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "TODO(INFRA): docs slim\n"],
        cwd=tmp_path,
        check=True,
    )
    result = _run_audit(tmp_path)
    assert "[L2] OK" in result.stdout, (
        f"L2 should accept non-numeric IDs; stdout={result.stdout!r}"
    )
    assert result.returncode == 0