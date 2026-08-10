#!/usr/bin/env bash
# scripts/setup-node.sh — ai-github-radar
# 装 Node 环境（pnpm），路径锁在项目内
# 脚手架 agent-loop-scaffold 不自带，本项目补充

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WEB_DIR="$REPO_ROOT/app/web"

# 锁死项目内路径（沙箱硬约束 §6）
export NPM_CONFIG_CACHE="$REPO_ROOT/.npm-global"
export PNPM_HOME="$REPO_ROOT/.pnpm-home"
export PATH="$REPO_ROOT/.pnpm-home:$PATH"

mkdir -p "$NPM_CONFIG_CACHE" "$PNPM_HOME"

echo "🔧 Node 环境配置"
echo "   NPM_CONFIG_CACHE = $NPM_CONFIG_CACHE"
echo "   PNPM_HOME        = $PNPM_HOME"

# 检查 Node
if ! command -v node >/dev/null 2>&1; then
  echo "❌ node 没装。请先装 Node 22+（推荐 nvm 或 fnm）"
  exit 1
fi

NODE_VER=$(node --version | sed 's/v//')
NODE_MAJOR=$(echo "$NODE_VER" | cut -d. -f1)
if [ "$NODE_MAJOR" -lt 22 ]; then
  echo "⚠️  Node $NODE_VER < 22，建议升级到 22+（.nvmrc 锁定）"
fi

# 检查 pnpm
if ! command -v pnpm >/dev/null 2>&1; then
  echo "📦 装 pnpm..."
  npm install -g pnpm@latest
fi

echo "✓ Node: $(node --version)"
echo "✓ pnpm: $(pnpm --version)"

# 装项目依赖
if [ -f "$WEB_DIR/package.json" ]; then
  echo "📦 装 app/web 依赖..."
  cd "$WEB_DIR"
  pnpm install --prefer-offline
  echo "✓ 依赖装好"
fi

echo ""
echo "✅ Node 环境就绪"
echo "   启动开发: cd app/web && pnpm dev"