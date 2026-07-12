# SwiftBar 余量监控（Codex + Claude）

按 Obsidian 笔记《菜单栏显示 Codex + Claude 剩余用量》的思路实现的干净版：
**不含世界杯内容**，可在新机器上一条命令部署。

标题栏效果：`Cdx 39%/6% ⇢17:42 Cld 74%/46% ⇢19:20`
（斜杠前 = 5 小时窗口剩余，后 = 周窗口剩余；箭头后 = 5h 窗口重置时间；`?` = 该侧没取到数；数字带 `*` = 缓存值）

## 安装（在目标 Mac 上）

```bash
curl -fsSL https://raw.githubusercontent.com/iamkickBJ/workouts_page/claude/swiftbar-quota-monitoring-9zgs8f/swiftbar/install.sh | bash
```

或在本仓库目录内 `bash swiftbar/install.sh`。脚本会：装 SwiftBar（如缺）→ 插件目录设为
`~/.swiftbar` → 部署 `codex-claude-usage.2m.js` 并把 shebang 改写为**本机实际 node 路径**
→ 关闭 `MakePluginExecutable` → 备份旧插件到 `~/.swiftbar-backups/`（去执行权限）→
清理插件目录里多余的可执行文件 → 冒烟测试 → 启动 SwiftBar。

前置：node；Codex 需 ChatGPT 账号 `codex login`（API key 模式读不到限额）；Claude Code 已登录。

## 取数方案（对齐笔记结论）

| 侧 | 主路径 | 兜底 |
|---|---|---|
| Codex | 官方 `codex app-server` JSON-RPC（`initialize` → `initialized` → `account/rateLimits/read`，实时、无 ToS 问题） | CodexBar CLI |
| Claude | CodexBar CLI（`codexbar usage --provider claude --source auto`） | NAS 借数（≤4 分钟新鲜）→ Claude Code OAuth `api.anthropic.com/api/oauth/usage` |

已内置笔记里踩过的坑的对策：

- **UA 死桶**：OAuth 请求 UA 固定 `claude-code/2.1.81`。非 `claude-code/` UA 有专门的极严限流桶，会无视频率持续 429——别改。
- **90 秒去重缓存**（必须 < 2 分钟刷新间隔，否则成"假刷新"）；429 按 `retry-after` 写入
  `~/.swiftbar/.claude_usage_cache.json` 的 `blockUntil` 退避，退避期不硬催（会加长惩罚）。
- 故障/退避期间最多把 **15 分钟内**的旧值当展示值，数字带 `*`，下拉标明缓存年龄，不拿旧数冒充实时。
- 开机自启 PATH 精简问题：脚本内写死 PATH 前缀，shebang 由 install.sh 按机器改写。
- 插件目录顶层只保留主插件一个可执行文件；备份统一进 `~/.swiftbar-backups/`。

## NAS / 手机看板（可选）

本仓库公开，**NAS 密钥与看板地址不入库**。需要时在目标机创建
`~/.swiftbar-support/usage-monitor.json`（值见 Obsidian 笔记）：

```json
{"nasUrl": "http://<NAS_IP>:8787", "nasKey": "<X-Token>", "dashboardUrl": "https://<域名>/usage/?k=<key>"}
```

配置后：Claude 侧会优先借用 NAS 上其他机器 4 分钟内的新鲜数据（免打接口），下拉底部出现「手机看板」入口。
本版**只读不上报**（POST 上报格式以 NAS `server.py` 为准，避免猜格式污染数据）。

## 与笔记完整版（Air/mini 现役 + iCloud 资产目录）的差异

- 无世界杯内容（按 2026-07 决定移除）
- 无 Claude Desktop Cookie 适配器、无本地 token 统计（今日/昨日/累计）、无 NAS 上报——
  这些在 vault 的 `workflows/assets/菜单栏用量监控/` 资产目录里，需要时按其 README 叠加
- Air/mini 上的现役插件不受影响；本安装脚本若检测到同名旧插件会先备份再覆盖

## 排障速查（摘自笔记）

```bash
# curl 直测 Claude 接口，一眼定位问题类别
TOKEN=$(security find-generic-password -s "Claude Code-credentials" -w | python3 -c 'import sys,json;print(json.load(sys.stdin)["claudeAiOauth"]["accessToken"])')
curl -sS -o /dev/null -w "HTTP %{http_code}\n" \
  -H "Authorization: Bearer $TOKEN" -H "anthropic-beta: oauth-2025-04-20" \
  -H "User-Agent: claude-code/2.1.81" https://api.anthropic.com/api/oauth/usage
```

- `200` 而界面仍不对 → 删 `~/.swiftbar/.claude_usage_cache.json` 重跑一次（注意是隐藏文件，`ls -la` 才看得到）
- `401` → token 过期：`claude -p hi` 刷新，长期没用则 `/login`（`claude auth status` 显示 loggedIn 不代表凭证可用）
- `429` → 正常退避等它，别删缓存硬催
- `Cdx ?` → codex 未装/未登录/非 ChatGPT 登录态
- 整条消失 → shebang node 路径不对（`bad interpreter`），重跑 install.sh；或刘海挤占（装 Ice 整理菜单栏）
