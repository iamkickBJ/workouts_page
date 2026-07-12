#!/bin/bash
# 在 macOS 上部署「Codex + Claude 余量监控」SwiftBar 插件（不含世界杯内容）。
# 用法（仓库内）:  bash swiftbar/install.sh
# 用法（一键）:    curl -fsSL https://raw.githubusercontent.com/iamkickBJ/workouts_page/claude/swiftbar-quota-monitoring-9zgs8f/swiftbar/install.sh | bash
set -euo pipefail

PLUGIN="codex-claude-usage.2m.js"
RAW_URL="https://raw.githubusercontent.com/iamkickBJ/workouts_page/claude/swiftbar-quota-monitoring-9zgs8f/swiftbar/${PLUGIN}"
PLUGIN_DIR="$HOME/.swiftbar"
DEST="$PLUGIN_DIR/$PLUGIN"

if [[ "$(uname)" != "Darwin" ]]; then
  echo "SwiftBar 仅支持 macOS，请在 Mac 上运行本脚本。" >&2
  exit 1
fi

# 前置：node 必须有（shebang 要写死它的实际路径，否则开机自启时整条消失）
NODE_BIN="$(command -v node || true)"
if [[ -z "$NODE_BIN" ]]; then
  echo "未检测到 node，请先: brew install node" >&2
  exit 1
fi

# SwiftBar 本体
if [[ ! -d "/Applications/SwiftBar.app" && ! -d "$HOME/Applications/SwiftBar.app" ]]; then
  if ! command -v brew >/dev/null 2>&1; then
    echo "未检测到 Homebrew，请先安装: https://brew.sh" >&2
    exit 1
  fi
  echo "==> 安装 SwiftBar ..."
  brew install --cask swiftbar
fi

mkdir -p "$PLUGIN_DIR" "$HOME/.swiftbar-support" "$HOME/.swiftbar-backups"
defaults write com.ameba.SwiftBar PluginDirectory "$PLUGIN_DIR"
# 防止 SwiftBar 自动把支持文件/备份设为可执行后当成插件加载
defaults write com.ameba.SwiftBar MakePluginExecutable -bool false

# 先退出 SwiftBar，避免部署过程中加载到中间状态
killall SwiftBar 2>/dev/null || true

# 旧插件备份到 ~/.swiftbar-backups（去掉执行权限——可执行备份留在插件目录会被 SwiftBar 当第二个插件）
if [[ -f "$DEST" ]]; then
  BAK="$HOME/.swiftbar-backups/${PLUGIN}.$(date +%Y%m%d-%H%M%S).bak"
  cp "$DEST" "$BAK" && chmod a-x "$BAK"
  echo "==> 旧插件已备份: $BAK"
fi

# 清理早期 Python 版残留（v1，标题形如 "C -- · X 33%"）
rm -f "$PLUGIN_DIR/codex_claude_quota.5m.py"

# 部署（仓库内直接拷；curl|bash 场景从 GitHub 下载）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
if [[ -n "$SCRIPT_DIR" && -f "$SCRIPT_DIR/$PLUGIN" ]]; then
  cp "$SCRIPT_DIR/$PLUGIN" "$DEST"
else
  echo "==> 从 GitHub 下载插件 ..."
  curl -fsSL "$RAW_URL" -o "$DEST"
fi

# shebang 写死本机 node 实际路径（Air 在 /usr/local/bin，mini 在 /opt/homebrew/bin，写错整条消失）
sed -i '' "1s|.*|#!${NODE_BIN}|" "$DEST"
chmod +x "$DEST"

# 插件目录顶层只保留主插件一个文件——SwiftBar 连普通支持文件都会建状态项，
# 其余一律移到 ~/.swiftbar-backups/stray-*/（隐藏文件如 .claude_usage_cache.json 不受影响）
STRAY_DIR="$HOME/.swiftbar-backups/stray-$(date +%Y%m%d-%H%M%S)"
for f in "$PLUGIN_DIR"/*; do
  base="$(basename "$f")"
  if [[ -f "$f" && "$base" != "$PLUGIN" ]]; then
    mkdir -p "$STRAY_DIR"
    mv "$f" "$STRAY_DIR/$base"
    chmod a-x "$STRAY_DIR/$base" 2>/dev/null || true
    echo "==> 已移出插件目录: $base → $STRAY_DIR/"
  fi
done

# 前置检查（只提醒，不阻断）
command -v codex >/dev/null 2>&1 || echo "⚠️  未检测到 codex（npm install -g @openai/codex），且必须 ChatGPT 账号 codex login，否则 Cdx 显示 ?"
command -v claude >/dev/null 2>&1 || echo "⚠️  未检测到 claude（Claude Code），Claude 侧将依赖 CodexBar/NAS 取数"

echo "==> 冒烟测试（首行应为 Cdx xx%/xx% ... Cld xx%/xx% ...）:"
"$DEST" | head -1 || true

open -a SwiftBar
cat <<'TIP'
==> 完成。
    · SwiftBar 首次启动若询问插件文件夹，按 Cmd+Shift+G 输入 ~/.swiftbar
    · NAS/手机看板（可选，密钥不入库）: 创建 ~/.swiftbar-support/usage-monitor.json
      {"nasUrl":"http://<NAS_IP>:8787","nasKey":"<X-Token>","dashboardUrl":"https://<域名>/usage/?k=<key>"}
    · 开机自启:
      osascript -e 'tell application "System Events" to make login item at end with properties {path:"/Applications/SwiftBar.app", hidden:false}'
TIP
