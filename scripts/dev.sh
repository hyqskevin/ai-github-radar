#!/usr/bin/env bash
# scripts/dev.sh — 统一启动脚本
# 同时拉起 Python daemon + Nuxt dev server
# 阶段一单机，绑 127.0.0.1
#
# 用法:
#   ./scripts/dev.sh             # 全启（后端 + 前端）
#   ./scripts/dev.sh --backend   # 只启后端
#   ./scripts/dev.sh --frontend  # 只启前端
#
# 停止:
#   Ctrl-C 两下（一次停前端，一次停后端）

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo "🛑 正在关闭..."
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  exit 0
}

trap cleanup SIGINT SIGTERM

start_backend() {
  echo "🐍 启动 Python daemon (127.0.0.1:8765)..."
  cd "$REPO_ROOT"
  uv run python -m ai_github_radar.cli daemon --host 127.0.0.1 --port 8765 &
  BACKEND_PID=$!
}

start_frontend() {
  echo "🌐 启动 Nuxt 4 dev server (127.0.0.1:5173)..."
  cd "$REPO_ROOT/app/web"
  pnpm dev &
  FRONTEND_PID=$!
}

case "${1:-}" in
  --backend)  start_backend; wait $BACKEND_PID ;;
  --frontend) start_frontend; wait $FRONTEND_PID ;;
  *)
    start_backend
    sleep 2
    start_frontend
    echo ""
    echo "✅ 已启动:"
    echo "   后端 daemon:  http://127.0.0.1:8765"
    echo "   前端 dashboard: http://127.0.0.1:5173"
    echo ""
    echo "按 Ctrl-C 停止"
    wait
    ;;
esac