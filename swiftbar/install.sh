#!/bin/bash
# 在 macOS 上安装 SwiftBar 并部署 Claude/Codex 余量监控插件。
# 用法（仓库内）:  bash swiftbar/install.sh
# 用法（一键）:    curl -fsSL https://raw.githubusercontent.com/iamkickBJ/workouts_page/claude/swiftbar-quota-monitoring-9zgs8f/swiftbar/install.sh | bash
set -euo pipefail

PLUGIN_NAME="codex_claude_quota.5m.py"
RAW_URL="https://raw.githubusercontent.com/iamkickBJ/workouts_page/claude/swiftbar-quota-monitoring-9zgs8f/swiftbar/${PLUGIN_NAME}"

if [[ "$(uname)" != "Darwin" ]]; then
  echo "SwiftBar 仅支持 macOS，请在 Mac 上运行本脚本。" >&2
  exit 1
fi

# 1. 安装 SwiftBar（如未安装）
if [[ ! -d "/Applications/SwiftBar.app" && ! -d "$HOME/Applications/SwiftBar.app" ]]; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "未检测到 Homebrew，请先安装: https://brew.sh" >&2
    exit 1
  fi
  echo "==> 安装 SwiftBar ..."
  brew install --cask swiftbar
else
  echo "==> SwiftBar 已安装，跳过"
fi

# 2. 确定插件目录（沿用已有设置，否则用 ~/.swiftbar）
PLUGIN_DIR="$(defaults read com.ameba.SwiftBar PluginDirectory 2>/dev/null || true)"
if [[ -z "${PLUGIN_DIR}" ]]; then
  PLUGIN_DIR="$HOME/.swiftbar"
  defaults write com.ameba.SwiftBar PluginDirectory "$PLUGIN_DIR"
fi
mkdir -p "$PLUGIN_DIR"
echo "==> 插件目录: $PLUGIN_DIR"

# 3. 部署插件（优先用仓库里的文件，curl|bash 场景则从 GitHub 下载）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
if [[ -n "$SCRIPT_DIR" && -f "$SCRIPT_DIR/$PLUGIN_NAME" ]]; then
  cp "$SCRIPT_DIR/$PLUGIN_NAME" "$PLUGIN_DIR/$PLUGIN_NAME"
else
  echo "==> 从 GitHub 下载插件 ..."
  curl -fsSL "$RAW_URL" -o "$PLUGIN_DIR/$PLUGIN_NAME"
fi
chmod +x "$PLUGIN_DIR/$PLUGIN_NAME"
echo "==> 插件已部署: $PLUGIN_DIR/$PLUGIN_NAME"

# 4. 启动 / 刷新 SwiftBar
open -a SwiftBar
echo "==> 完成。菜单栏应显示类似 “C 34% · X 12%”（C=Claude, X=Codex）。"
echo "    首次启动 SwiftBar 若询问插件目录，选择: $PLUGIN_DIR"
