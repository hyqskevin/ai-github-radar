"""tests/unit/scripts/test_ci_workflows.py — .github/workflows/* YAML 验证 (T121-T123).

校验:
- YAML 合法
- backend / frontend / ci 三个 workflow 都在
- 触发器有 push + pull_request
- 关键步骤名在 backend (ruff, pytest, audit-loop)
- 关键步骤名在 frontend (pnpm test, playwright)
- paths: 触发过滤正确(避免前端 PR 触发后端 CI)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def _load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text())


# ---------------------------------------------------------------------------
# 文件存在 + YAML 合法
# ---------------------------------------------------------------------------


def test_workflows_dir_exists() -> None:
    assert WORKFLOWS.is_dir()


@pytest.mark.parametrize(
    "name",
    ["backend-ci.yml", "frontend-ci.yml", "ci.yml"],
)
def test_workflow_yaml_valid(name: str) -> None:
    """三个 workflow YAML 必须合法。"""
    d = _load(name)
    assert "jobs" in d
    assert isinstance(d["jobs"], dict)


# ---------------------------------------------------------------------------
# backend-ci.yml
# ---------------------------------------------------------------------------


def test_backend_ci_has_test_job() -> None:
    d = _load("backend-ci.yml")
    assert "test" in d["jobs"]
    job = d["jobs"]["test"]
    assert job["runs-on"] == "ubuntu-latest"


def test_backend_ci_triggers() -> None:
    d = _load("backend-ci.yml")
    on = d.get(True) or d.get("on") or {}
    assert "push" in on
    assert "pull_request" in on


def test_backend_ci_paths_filter() -> None:
    """backend-ci 必须在 pr 上限定路径(避免前端 PR 误触发)。"""
    d = _load("backend-ci.yml")
    pr = d[True]["pull_request"] if True in d else d["on"]["pull_request"]
    assert "paths" in pr, "paths filter required to skip frontend-only PRs"
    paths = pr["paths"]
    assert any("backend/" in p for p in paths)
    assert any("tests/" in p for p in paths)


def test_backend_ci_includes_ruff() -> None:
    d = _load("backend-ci.yml")
    job = d["jobs"]["test"]
    steps_text = yaml.safe_dump(job["steps"])
    assert "ruff check" in steps_text
    assert "ruff format" in steps_text


def test_backend_ci_includes_audit_and_design_check() -> None:
    d = _load("backend-ci.yml")
    job = d["jobs"]["test"]
    steps_text = yaml.safe_dump(job["steps"])
    assert "audit-loop" in steps_text
    assert "design-check" in steps_text


def test_backend_ci_runs_pytest_with_coverage() -> None:
    d = _load("backend-ci.yml")
    job = d["jobs"]["test"]
    steps_text = yaml.safe_dump(job["steps"])
    assert "pytest" in steps_text
    assert "cov" in steps_text
    assert "fail-under" in steps_text, "must enforce coverage threshold"


# ---------------------------------------------------------------------------
# frontend-ci.yml
# ---------------------------------------------------------------------------


def test_frontend_ci_has_test_and_e2e_jobs() -> None:
    d = _load("frontend-ci.yml")
    jobs = d["jobs"]
    assert "test" in jobs
    assert "e2e" in jobs


def test_frontend_ci_paths_filter() -> None:
    d = _load("frontend-ci.yml")
    on = d.get(True) or d.get("on") or {}
    pr = on["pull_request"]
    assert "paths" in pr
    assert any("frontend/" in p for p in pr["paths"])


def test_frontend_ci_runs_pnpm_test() -> None:
    d = _load("frontend-ci.yml")
    test_job = d["jobs"]["test"]
    steps_text = yaml.safe_dump(test_job["steps"])
    assert "pnpm test" in steps_text or "vitest" in steps_text.lower()


def test_frontend_ci_runs_build() -> None:
    d = _load("frontend-ci.yml")
    test_job = d["jobs"]["test"]
    steps_text = yaml.safe_dump(test_job["steps"])
    assert "pnpm build" in steps_text


def test_frontend_ci_runs_playwright() -> None:
    d = _load("frontend-ci.yml")
    e2e_job = d["jobs"]["e2e"]
    steps_text = yaml.safe_dump(e2e_job["steps"])
    assert "playwright" in steps_text.lower()
    assert "chromium" in steps_text.lower()


def test_frontend_ci_installs_playwright_browser() -> None:
    """e2e 必须装 chromium — 没它跑会 fail。"""
    d = _load("frontend-ci.yml")
    e2e_job = d["jobs"]["e2e"]
    steps_text = yaml.safe_dump(e2e_job["steps"])
    assert "playwright install" in steps_text


def test_frontend_ci_uploads_report_on_failure() -> None:
    """失败时 upload Playwright 报告,方便 debug。"""
    d = _load("frontend-ci.yml")
    e2e_job = d["jobs"]["e2e"]
    steps_text = yaml.safe_dump(e2e_job["steps"])
    assert "upload-artifact" in steps_text
    assert "failure" in steps_text


# ---------------------------------------------------------------------------
# ci.yml 总入口
# ---------------------------------------------------------------------------


def test_ci_uses_reusable_workflows() -> None:
    """ci.yml 用 reusable workflow (uses:) 而不是 jobs inline。"""
    d = _load("ci.yml")
    for job in d["jobs"].values():
        assert "uses" in job, "ci.yml should delegate via reusable workflow"


def test_ci_calls_backend_and_frontend() -> None:
    d = _load("ci.yml")
    jobs = d["jobs"]
    assert "backend" in jobs
    assert "frontend" in jobs


def test_ci_no_duplicate_setup_steps() -> None:
    """ci.yml 只调 reusable,不重复 setup。"""
    d = _load("ci.yml")
    for job in d["jobs"].values():
        # 没 setup-python/setup-node/setup-pnpm 这种
        assert "steps" not in job or len(job.get("steps", [])) == 0