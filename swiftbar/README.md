# SwiftBar 余量监控（Claude Code + Codex）

在 macOS 菜单栏实时显示 Claude Code 和 Codex 的额度使用情况，每 5 分钟自动刷新。

菜单栏显示 `C 34% · X 12%`（C = Claude 5 小时窗口已用，X = Codex 5 小时窗口已用），
任一窗口用量 ≥ 90% 时标题会带 ⚠️。点开可看各窗口明细和重置时间：

- **Claude Code**：5 小时 / 7 天（含 Opus、Sonnet 细分，接口返回什么就显示什么）
- **Codex**：5 小时（primary）/ 7 天（secondary）窗口

## 安装

在 Mac 上执行一条命令：

```bash
curl -fsSL https://raw.githubusercontent.com/iamkickBJ/workouts_page/claude/swiftbar-quota-monitoring-9zgs8f/swiftbar/install.sh | bash
```

或者在本仓库目录内：

```bash
bash swiftbar/install.sh
```

脚本会自动：安装 SwiftBar（Homebrew cask，如未装）→ 设置插件目录（默认 `~/.swiftbar`，
已配置过则沿用）→ 部署插件并启动 SwiftBar。

## 数据来源

- **Claude**：从 macOS 钥匙串（`Claude Code-credentials`）或 `~/.claude/.credentials.json`
  读取 Claude Code 的 OAuth token，请求 `https://api.anthropic.com/api/oauth/usage`。
  token 过期时插件会提示，打开 Claude Code 随便跑一条命令即可刷新。
- **Codex**：不发网络请求，解析 `~/.codex/sessions/` 里最近会话记录中的
  `rate_limits` 事件。数据带有“N 分钟前”标注；很久没用 Codex 时数据会偏旧。

## 阈值颜色

绿色 < 70% ≤ 橙色 < 90% ≤ 红色。可在 `codex_claude_quota.5m.py` 顶部的
`WARN` / `DANGER` 常量里调整；刷新频率改文件名里的 `5m` 即可（SwiftBar 约定）。
