"""tests/unit/scripts/test_local_deploy.py — launchd plist + systemd unit 模板测试.

验证:
- 模板 sed 替换后是合法 XML / INI
- 关键占位符 (@PROJECT_ROOT@, @PYTHON_BIN@, @LOG_DIR@) 都被替换
- install 脚本存在 + 可执行 + dry-run 不破坏系统
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = REPO_ROOT / "scripts"
TEMPLATES = SCRIPTS / "templates"


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd or REPO_ROOT
    )


def _sed_template(template: Path, replacements: dict[str, str]) -> str:
    """模拟 install 脚本的 sed 替换,返 output string."""
    text = template.read_text()
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


# ---------------------------------------------------------------------------
# launchd plist 模板
# ---------------------------------------------------------------------------


def test_launchd_template_exists() -> None:
    assert (TEMPLATES / "com.ai-github-radar.scanner.plist").exists()


def test_launchd_template_placeholders() -> None:
    """模板必须含 4 个占位符(@PROJECT_ROOT@ @PYTHON_BIN@ @LOG_DIR@)。"""
    text = (TEMPLATES / "com.ai-github-radar.scanner.plist").read_text()
    for ph in ("@PROJECT_ROOT@", "@PYTHON_BIN@", "@LOG_DIR@"):
        assert ph in text, f"missing placeholder: {ph}"


def test_launchd_template_sed_valid_xml(tmp_path: Path) -> None:
    """sed 替换后产生合法 XML(plutil -lint 或 xml.etree)。"""
    src = TEMPLATES / "com.ai-github-radar.scanner.plist"
    out = tmp_path / "out.plist"
    rendered = _sed_template(src, {
        "@PROJECT_ROOT@": "/tmp/repo",
        "@PYTHON_BIN@": "/tmp/repo/.venv/bin/python",
        "@LOG_DIR@": "/tmp/logs",
    })
    out.write_text(rendered)
    # 用 xml.etree 验证合法(无 plutil 也不慌)
    import xml.etree.ElementTree as ET
    tree = ET.parse(out)
    root = tree.getroot()
    assert root.tag == "plist"
    # 找 Label + ProgramArguments + StartInterval
    text = rendered
    assert "com.ai-github-radar.scanner" in text
    assert "<integer>86400</integer>" in text
    assert "<key>RunAtLoad</key>" in text
    assert "SuccessfulExit" in text


def test_launchd_template_uses_24h_interval() -> None:
    """StartInterval 必须 86400 = 24h。"""
    text = (TEMPLATES / "com.ai-github-radar.scanner.plist").read_text()
    assert "<key>StartInterval</key>" in text
    assert "<integer>86400</integer>" in text


def test_launchd_template_keepalive_not_persistent() -> None:
    """KeepAlive 必须 false(成功/崩溃都不重启)。"""
    text = (TEMPLATES / "com.ai-github-radar.scanner.plist").read_text()
    assert "SuccessfulExit" in text
    assert "<false/>" in text


# ---------------------------------------------------------------------------
# systemd unit / timer 模板
# ---------------------------------------------------------------------------


def test_systemd_service_template_exists() -> None:
    assert (TEMPLATES / "ai-github-radar-scan.service").exists()


def test_systemd_timer_template_exists() -> None:
    assert (TEMPLATES / "ai-github-radar-scan.timer").exists()


def test_systemd_service_template_placeholders() -> None:
    text = (TEMPLATES / "ai-github-radar-scan.service").read_text()
    for ph in ("@PROJECT_ROOT@", "@PYTHON_BIN@", "@LOG_DIR@"):
        assert ph in text


def test_systemd_service_template_oneshot() -> None:
    text = (TEMPLATES / "ai-github-radar-scan.service").read_text()
    assert "Type=oneshot" in text
    assert "ExecStart=" in text
    assert "ai_github_radar" in text
    assert "scan" in text


def test_systemd_timer_24h() -> None:
    text = (TEMPLATES / "ai-github-radar-scan.timer").read_text()
    assert "OnUnitActiveSec=24h" in text
    assert "Persistent=true" in text


def test_systemd_service_renders_to_valid_ini(tmp_path: Path) -> None:
    """sed 后产出 INI 文件 configparser 能解析。"""
    src = TEMPLATES / "ai-github-radar-scan.service"
    rendered = _sed_template(src, {
        "@PROJECT_ROOT@": "/tmp/repo",
        "@PYTHON_BIN@": "/tmp/repo/.venv/bin/python",
        "@LOG_DIR@": "/tmp/logs",
    })
    out = tmp_path / "test.service"
    out.write_text(rendered)

    import configparser
    cfg = configparser.ConfigParser()
    cfg.read(out)
    assert cfg.sections(), "no sections"
    assert "Unit" in cfg.sections()
    assert "Service" in cfg.sections()
    assert cfg.get("Service", "Type") == "oneshot"
    assert "ai_github_radar" in cfg.get("Service", "ExecStart")
    assert "WorkingDirectory=/tmp/repo" in rendered


# ---------------------------------------------------------------------------
# install 脚本
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="posix only")
def test_install_launchd_script_exists() -> None:
    p = SCRIPTS / "install-launchd.sh"
    assert p.exists()
    assert os.access(p, os.X_OK), f"install-launchd.sh not executable: {p}"


@pytest.mark.skipif(sys.platform == "win32", reason="posix only")
def test_install_systemd_script_exists() -> None:
    p = SCRIPTS / "install-systemd.sh"
    assert p.exists()
    assert os.access(p, os.X_OK)


def test_dev_sh_exists() -> None:
    p = SCRIPTS / "dev.sh"
    assert p.exists()
    assert os.access(p, os.X_OK)


def test_uninstall_scripts_exist() -> None:
    for name in ("uninstall-launchd.sh", "uninstall-systemd.sh"):
        p = SCRIPTS / name
        assert p.exists(), f"missing {name}"
        assert os.access(p, os.X_OK), f"{name} not executable"


# ---------------------------------------------------------------------------
# install-launchd.sh dry-run
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "Darwin", reason="macOS only")
def test_install_launchd_dry_run(tmp_path: Path) -> None:
    """macOS 上 --dry-run 不写 ~/Library/LaunchAgents/。"""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    script = SCRIPTS / "install-launchd.sh"
    p = _run(
        [
            str(script),
            "--dry-run",
            "--project-root", str(REPO_ROOT),
            "--user-home", str(fake_home),
        ]
    )
    assert p.returncode == 0, f"stderr={p.stderr}\nstdout={p.stdout}"
    assert not (fake_home / "Library" / "LaunchAgents").exists() or \
        not (fake_home / "Library" / "LaunchAgents" / "com.ai-github-radar.scanner.plist").exists()
    assert "dry-run" in p.stdout.lower() or "[DRY-RUN]" in p.stdout


@pytest.mark.skipif(sys.platform != "Linux", reason="Linux only")
def test_install_systemd_dry_run(tmp_path: Path) -> None:
    """Linux 上 --dry-run 不写 ~/.config/systemd/user/。"""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    script = SCRIPTS / "install-systemd.sh"
    p = _run(
        [
            str(script),
            "--dry-run",
            "--project-root", str(REPO_ROOT),
            "--user-home", str(fake_home),
        ]
    )
    assert p.returncode == 0, f"stderr={p.stderr}\nstdout={p.stdout}"
    assert not (fake_home / ".config" / "systemd" / "user").exists() or \
        not (fake_home / ".config" / "systemd" / "user" / "ai-github-radar-scan.service").exists()