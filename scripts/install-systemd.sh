#!/usr/bin/env bash
# install-systemd.sh — Linux systemd user service + timer 安装 (T117/T119)
#
# 把 .service + .timer 模板替换占位符后写到 ~/.config/systemd/user/,
# 然后 systemctl --user enable + start timer。
#
# 用法: 同 install-launchd.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SVC_TEMPLATE="$SCRIPT_DIR/templates/ai-github-radar-scan.service"
TIMER_TEMPLATE="$SCRIPT_DIR/templates/ai-github-radar-scan.timer"

DRY_RUN=false
PROJECT_ROOT="$REPO_ROOT"
USER_HOME="${HOME}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true; shift ;;
        --project-root) PROJECT_ROOT="$2"; shift 2 ;;
        --user-home) USER_HOME="$2"; shift 2 ;;
        -h|--help)
            grep '^# ' "$0" | sed 's/^# //'
            exit 0
            ;;
        *) echo "ERROR: unknown arg: $1" >&2; exit 2 ;;
    esac
done

PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
LOG_DIR="$PROJECT_ROOT/data/logs"
SYSTEMD_DIR="$USER_HOME/.config/systemd/user"

log() { echo "[install-systemd] $*"; }
err() { echo "[install-systemd] ERROR: $*" >&2; exit 1; }

# 平台检查
[[ "$(uname -s)" == "Linux" ]] || err "not Linux (got $(uname -s)). use install-launchd.sh on macOS"

# 前置
[[ -f "$SVC_TEMPLATE" ]] || err "service template missing: $SVC_TEMPLATE"
[[ -f "$TIMER_TEMPLATE" ]] || err "timer template missing: $TIMER_TEMPLATE"
[[ -x "$PYTHON_BIN" ]] || err "python not found / not executable: $PYTHON_BIN (run scripts/setup-python.sh)"

command -v systemctl >/dev/null || err "systemctl not found; need systemd"

log "project_root=$PROJECT_ROOT"
log "python_bin=$PYTHON_BIN"
log "log_dir=$LOG_DIR"
log "systemd_dir=$SYSTEMD_DIR"

if $DRY_RUN; then
    log "[DRY-RUN] would create $SYSTEMD_DIR/ai-github-radar-scan.{service,timer}"
    log "[DRY-RUN] would run: systemctl --user enable --now ai-github-radar-scan.timer"
    exit 0
fi

mkdir -p "$SYSTEMD_DIR" "$LOG_DIR"

# 用 Python 替换占位符
python3 - "$SVC_TEMPLATE" "$SYSTEMD_DIR/ai-github-radar-scan.service" "$PROJECT_ROOT" "$PYTHON_BIN" "$LOG_DIR" <<'PYEOF'
import sys, pathlib
tmpl, target, root, pybin, logdir = sys.argv[1:6]
content = pathlib.Path(tmpl).read_text()
repls = {
    "@PROJECT_ROOT@": root,
    "@PYTHON_BIN@": pybin,
    "@LOG_DIR@": logdir,
}
for k, v in repls.items():
    content = content.replace(k, v)
pathlib.Path(target).write_text(content)
print(f"[install-systemd] wrote {target} ({len(content)} bytes)")
PYEOF

# timer 模板没有占位符,直接 cp
cp "$TIMER_TEMPLATE" "$SYSTEMD_DIR/ai-github-radar-scan.timer"
log "copied timer template → $SYSTEMD_DIR/ai-github-radar-scan.timer"

# 重载 + enable
systemctl --user daemon-reload
systemctl --user enable --now ai-github-radar-scan.timer

# 验证
if systemctl --user list-timers | grep -q "ai-github-radar-scan"; then
    log "✓ ai-github-radar-scan.timer active"
    log "  - logs: $LOG_DIR/scanner.{log,err}"
    log "  - list: systemctl --user list-timers"
    log "  - stop: systemctl --user disable --now ai-github-radar-scan.timer"
    log ""
    log "TIP: enable lingering to run timer even after logout:"
    log "  sudo loginctl enable-linger \$USER"
else
    err "systemctl enable failed; check 'journalctl --user -xe'"
fi