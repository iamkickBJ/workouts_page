#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# <xbar.title>Claude & Codex 余量监控</xbar.title>
# <xbar.version>v1.0</xbar.version>
# <xbar.author>iamkick</xbar.author>
# <xbar.desc>在菜单栏显示 Claude Code 与 Codex 的额度使用情况（5 小时窗口 + 周窗口）</xbar.desc>
# <xbar.dependencies>python3</xbar.dependencies>
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideDisablePlugin>false</swiftbar.hideDisablePlugin>
#
# Claude:  读取 Claude Code 的 OAuth token（macOS 钥匙串或 ~/.claude/.credentials.json），
#          调用 https://api.anthropic.com/api/oauth/usage 获取各窗口的使用百分比。
# Codex:   不发网络请求，直接解析 ~/.codex/sessions 里最近会话的 rate_limits 事件
#          （primary = 5h 窗口，secondary = 周窗口）。

import datetime
import glob
import json
import os
import subprocess
import urllib.request

CLAUDE_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
KEYCHAIN_SERVICE = "Claude Code-credentials"
CLAUDE_CRED_FILE = os.path.expanduser("~/.claude/.credentials.json")
CODEX_SESSIONS = os.path.expanduser("~/.codex/sessions")

WARN = 70
DANGER = 90


def color_for(pct):
    if pct is None:
        return "gray"
    if pct >= DANGER:
        return "red"
    if pct >= WARN:
        return "orange"
    return "green"


def fmt_pct(pct):
    return "--" if pct is None else f"{pct:.0f}%"


def fmt_reset(dt):
    if dt is None:
        return ""
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    dt = dt.astimezone()
    if dt.date() == now.date():
        return dt.strftime("今天 %H:%M 重置")
    return dt.strftime("%m-%d %H:%M 重置")


def parse_iso(s):
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


# ---------- Claude ----------

def claude_token():
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            return json.loads(out.stdout.strip()).get("claudeAiOauth", {})
    except Exception:
        pass
    try:
        with open(CLAUDE_CRED_FILE) as f:
            return json.load(f).get("claudeAiOauth", {})
    except Exception:
        return {}


def claude_usage():
    """Returns (rows, error). rows: list of (label, pct, reset_dt)."""
    oauth = claude_token()
    token = oauth.get("accessToken")
    if not token:
        return [], "未找到 Claude Code 登录凭证"
    expires = oauth.get("expiresAt")
    if expires and expires / 1000 < datetime.datetime.now().timestamp():
        return [], "token 已过期，打开 Claude Code 跑一条命令刷新"
    req = urllib.request.Request(CLAUDE_USAGE_URL, headers={
        "Authorization": f"Bearer {token}",
        "anthropic-beta": "oauth-2025-04-20",
        "User-Agent": "swiftbar-quota-monitor",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
    except Exception as e:
        return [], f"usage 接口请求失败: {e}"

    labels = [
        ("five_hour", "5 小时"),
        ("seven_day", "7 天"),
        ("seven_day_opus", "7 天 Opus"),
        ("seven_day_sonnet", "7 天 Sonnet"),
    ]
    rows = []
    for key, label in labels:
        item = data.get(key)
        if not isinstance(item, dict):
            continue
        pct = item.get("utilization")
        if pct is None:
            continue
        rows.append((label, float(pct), parse_iso(item.get("resets_at"))))
    if not rows:
        return [], "usage 接口返回了未知格式"
    return rows, None


# ---------- Codex ----------

def codex_usage():
    """Returns (rows, error, data_ts). Parses newest session jsonl for rate_limits."""
    files = sorted(
        glob.glob(os.path.join(CODEX_SESSIONS, "*", "*", "*", "rollout-*.jsonl")),
        key=os.path.getmtime, reverse=True,
    )[:5]
    if not files:
        return [], "未找到 Codex 会话记录（~/.codex/sessions）", None

    for path in files:
        last, ts = None, None
        try:
            with open(path, errors="ignore") as f:
                for line in f:
                    if '"rate_limits"' not in line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    payload = obj.get("payload", {})
                    rl = payload.get("rate_limits") or payload.get("info", {}).get("rate_limits")
                    if rl:
                        last, ts = rl, parse_iso(obj.get("timestamp"))
        except OSError:
            continue
        if last:
            rows = []
            for key in ("primary", "secondary"):
                win = last.get(key)
                if not isinstance(win, dict):
                    continue
                minutes = win.get("window_minutes") or 0
                if minutes >= 10080:
                    label = "7 天"
                elif minutes >= 60:
                    label = f"{minutes // 60} 小时"
                else:
                    label = key
                reset = None
                secs = win.get("resets_in_seconds")
                if secs is not None and ts is not None:
                    reset = ts + datetime.timedelta(seconds=secs)
                rows.append((label, float(win.get("used_percent", 0)), reset))
            if rows:
                return rows, None, ts
    return [], "最近会话里没有 rate_limits 数据，先用 Codex 跑一条命令", None


# ---------- Output ----------

def section(name, rows, error):
    print(name + " | size=13")
    if error:
        print(f"{error} | color=gray size=12")
        return
    for label, pct, reset in rows:
        extra = f"　{fmt_reset(reset)}" if reset else ""
        print(f"{label}：已用 {fmt_pct(pct)}{extra} | color={color_for(pct)} font=Menlo size=12")


def main():
    claude_rows, claude_err = claude_usage()
    codex_rows, codex_err, codex_ts = codex_usage()

    def head(rows):
        return fmt_pct(rows[0][1]) if rows else "--"

    worst = max([p for _, p, _ in claude_rows + codex_rows] or [0])
    icon = "⚠️ " if worst >= DANGER else ""
    print(f"{icon}C {head(claude_rows)} · X {head(codex_rows)}")
    print("---")
    section("Claude Code", claude_rows, claude_err)
    print("---")
    section("Codex", codex_rows, codex_err)
    if codex_ts:
        age = int((datetime.datetime.now(datetime.timezone.utc) - codex_ts).total_seconds() // 60)
        print(f"数据来自 {age} 分钟前的会话 | color=gray size=11")
    print("---")
    print("刷新 | refresh=true")


if __name__ == "__main__":
    main()
