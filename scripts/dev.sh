#!/usr/bin/env bash
# scripts/dev.sh — 一键起 Python 后端 + Nuxt 前端 (T118)
#
# 同时拉起:
#   后端: PYTHONPATH=src .venv/bin/python -m ai_github_radar.cli web --port 8765
#   前端: cd app/web && PYTHON_BACKEND_URL=http://127.0.0.1:8765 pnpm dev
#
# 设计: docs/superpowers/specs/2026-08-19-local-deploy-design.md
#
# 用法:
#   ./scripts/dev.sh                  # 起两端 (default)
#   ./scripts/dev.sh --backend        # 只起后端
#   ./scripts/dev.sh --frontend       # 只起前端
#   BACKEND_PORT=9000 ./scripts/dev.sh # 自定义端口
#
# 停止: Ctrl-C 一下,trap kill 两端
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8765}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

BACKEND_PID=""
FRONTEND_PID=""
LOG_DIR="$REPO_ROOT/data/logs"

mkdir -p "$LOG_DIR"

cleanup() {
    echo ""
    echo "🛑 stopping services..."
    if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null || true
        echo "  - frontend (PID $FRONTEND_PID) stopped"
    fi
    if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
        echo "  - backend (PID $BACKEND_PID) stopped"
    fi
    exit 0
}
trap cleanup SIGINT SIGTERM

# 检查 .venv
PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "❌ Python venv missing: $PYTHON_BIN"
    echo "   run: bash scripts/setup-python.sh"
    exit 1
fi

# 检查 node
if ! command -v pnpm >/dev/null 2>&1; then
    echo "❌ pnpm not found"
    echo "   run: bash scripts/setup-node.sh"
    exit 1
fi

start_backend() {
    echo "🐍 starting Python backend at http://$BACKEND_HOST:$BACKEND_PORT ..."
    cd "$REPO_ROOT"
    PYTHONPATH="$REPO_ROOT/backend" "$PYTHON_BIN" -m ai_github_radar.cli web \
        --host "$BACKEND_HOST" --port "$BACKEND_PORT" \
        > "$LOG_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
}

start_frontend() {
    echo "🌐 starting Nuxt dev server at http://127.0.0.1:$FRONTEND_PORT ..."
    cd "$REPO_ROOT/frontend"
    PYTHON_BACKEND_URL="http://$BACKEND_HOST:$BACKEND_PORT" \
        pnpm dev \
        > "$LOG_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!
}

wait_for_backend() {
    echo -n "  waiting for backend"
    for _ in $(seq 1 30); do
        if curl -sf "http://$BACKEND_HOST:$BACKEND_PORT/api/keywords" >/dev/null 2>&1; then
            echo " ✓ ready"
            return 0
        fi
        echo -n "."
        sleep 0.5
    done
    echo " ✗ timeout (check $LOG_DIR/backend.log)"
    return 1
}

case "${1:-}" in
    --backend)
        start_backend
        wait_for_backend
        echo ""
        echo "✅ backend only:"
        echo "   http://$BACKEND_HOST:$BACKEND_PORT"
        echo "   log: $LOG_DIR/backend.log"
        wait $BACKEND_PID
        ;;
    --frontend)
        start_frontend
        echo ""
        echo "✅ frontend only:"
        echo "   http://127.0.0.1:$FRONTEND_PORT"
        echo "   log: $LOG_DIR/frontend.log"
        echo "   (no backend integration; will fall back to mock store)"
        wait $FRONTEND_PID
        ;;
    -h|--help)
        grep '^# ' "$0" | sed 's/^# //'
        exit 0
        ;;
    *)
        start_backend
        wait_for_backend
        start_frontend
        echo ""
        echo "✅ both services up:"
        echo "   backend:  http://$BACKEND_HOST:$BACKEND_PORT"
        echo "   frontend: http://127.0.0.1:$FRONTEND_PORT"
        echo "   logs: $LOG_DIR/{backend,frontend}.log"
        echo ""
        echo "verify integration:"
        echo "   curl http://127.0.0.1:$FRONTEND_PORT/api/integration/health"
        echo ""
        echo "Press Ctrl-C to stop both."
        wait
        ;;
esac