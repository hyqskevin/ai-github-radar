#!/usr/bin/env bash
# uninstall-launchd.sh — 卸载 macOS launchd (T119)
set -euo pipefail
LABEL="com.ai-github-radar.scanner"
LAUNCH_AGENTS="${HOME}/Library/LaunchAgents"
TARGET="$LAUNCH_AGENTS/${LABEL}.plist"

if launchctl list | grep -q "$LABEL"; then
    launchctl unload "$TARGET" 2>/dev/null || true
    echo "[uninstall-launchd] unloaded $LABEL"
fi

if [[ -f "$TARGET" ]]; then
    rm "$TARGET"
    echo "[uninstall-launchd] removed $TARGET"
fi
echo "[uninstall-launchd] ✓ done (logs/data kept; run scripts/uninstall-systemd.sh on Linux)"