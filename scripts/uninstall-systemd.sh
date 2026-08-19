#!/usr/bin/env bash
# uninstall-systemd.sh — 卸载 Linux systemd user timer (T119)
set -euo pipefail
SYSTEMD_DIR="${HOME}/.config/systemd/user"

if systemctl --user list-timers 2>/dev/null | grep -q "ai-github-radar-scan"; then
    systemctl --user disable --now ai-github-radar-scan.timer
    echo "[uninstall-systemd] disabled ai-github-radar-scan.timer"
fi

for f in ai-github-radar-scan.service ai-github-radar-scan.timer; do
    if [[ -f "$SYSTEMD_DIR/$f" ]]; then
        rm "$SYSTEMD_DIR/$f"
        echo "[uninstall-systemd] removed $SYSTEMD_DIR/$f"
    fi
done
systemctl --user daemon-reload
echo "[uninstall-systemd] ✓ done (logs/data kept)"