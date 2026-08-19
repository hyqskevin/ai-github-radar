#!/usr/bin/env bash
# install-launchd.sh — macOS launchd 安装 (T116/T119)
#
# 把 scripts/templates/com.ai-github-radar.scanner.plist 模板
# 替换占位符后写到 ~/Library/LaunchAgents/, 然后 launchctl load 启动。
#
# 用法:
#   ./scripts/install-launchd.sh                    # 默认装在当前 repo + $HOME
#   ./scripts/install-launchd.sh --dry-run          # 只打印不写
#   ./scripts/install-launchd.sh --project-root DIR # 自定义路径
#   ./scripts/install-launchd.sh --user-home DIR    # 测试用 HOME
#
# 卸载: ./scripts/uninstall-launchd.sh
#
# 设计: docs/superpowers/specs/2026-08-19-local-deploy-design.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$SCRIPT_DIR/templates/com.ai-github-radar.scanner.plist"
LABEL="com.ai-github-radar.scanner"
PLIST_NAME="${LABEL}.plist"

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
LAUNCH_AGENTS="$USER_HOME/Library/LaunchAgents"

log() { echo "[install-launchd] $*"; }
err() { echo "[install-launchd] ERROR: $*" >&2; exit 1; }

# 平台检查
[[ "$(uname -s)" == "Darwin" ]] || err "not macOS (got $(uname -s)). use install-systemd.sh on Linux"

# 前置
[[ -f "$TEMPLATE" ]] || err "template missing: $TEMPLATE"
[[ -x "$PYTHON_BIN" ]] || err "python not found / not executable: $PYTHON_BIN (run scripts/setup-python.sh)"

log "project_root=$PROJECT_ROOT"
log "python_bin=$PYTHON_BIN"
log "log_dir=$LOG_DIR"
log "launch_agents=$LAUNCH_AGENTS"

if $DRY_RUN; then
    log "[DRY-RUN] would create $LAUNCH_AGENTS/$PLIST_NAME"
    log "[DRY-RUN] would create $LOG_DIR/"
    log "[DRY-RUN] would run: launchctl load $LAUNCH_AGENTS/$PLIST_NAME"
    exit 0
fi

mkdir -p "$LAUNCH_AGENTS" "$LOG_DIR"

# 用 Python 替换占位符(sed + 含空格路径会炸)
TARGET="$LAUNCH_AGENTS/$PLIST_NAME"
python3 - "$TEMPLATE" "$TARGET" "$PROJECT_ROOT" "$PYTHON_BIN" "$LOG_DIR" <<'PYEOF'
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
print(f"[install-launchd] wrote {target} ({len(content)} bytes)")
PYEOF

# 启 launchd
if launchctl list | grep -q "$LABEL"; then
    log "unloading existing $LABEL first"
    launchctl unload "$TARGET" 2>/dev/null || true
fi
launchctl load "$TARGET"
sleep 1

# 验证
if launchctl list | grep -q "$LABEL"; then
    log "✓ $LABEL loaded (will run once now, then every 24h)"
    log "  - logs: $LOG_DIR/scanner.{log,err}"
    log "  - stop:  launchctl unload $TARGET"
    log "  - run now: launchctl start $LABEL"
else
    err "launchctl load failed; check $LOG_DIR/scanner.err"
fi