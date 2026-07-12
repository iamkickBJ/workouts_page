#!/usr/bin/env node
/*
 * codex-claude-usage.2m.js — 菜单栏显示 Codex + Claude 剩余用量
 * 安装位置: ~/.swiftbar/codex-claude-usage.2m.js（install.sh 会把首行 shebang 改成本机 node 路径）
 *
 * <xbar.title>Codex & Claude 剩余用量</xbar.title>
 * <xbar.version>v2.0</xbar.version>
 * <xbar.desc>标题栏: Cdx 39%/6% ⇢17:42 Cld 74%/54% ⇢19:20（5小时窗/周窗剩余，箭头后为5h重置时间）</xbar.desc>
 * <xbar.dependencies>node,codex</xbar.dependencies>
 * <swiftbar.hideAbout>true</swiftbar.hideAbout>
 * <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
 *
 * 取数:
 *   Codex : 官方 `codex app-server` JSON-RPC（initialize → initialized → account/rateLimits/read），
 *           失败时 CodexBar CLI 兜底。必须 ChatGPT 账号登录（codex login），API key 模式读不到限额。
 *   Claude: CodexBar CLI → NAS 上其他机器的新鲜数据(≤4分钟) → Claude Code OAuth usage 接口。
 *           OAuth 请求 UA 必须是 claude-code/*，其他 UA 会进专用死桶（持续 429）。
 *   缓存  : Claude 侧 90 秒去重（必须小于文件名里的刷新间隔 2m，否则成"假刷新"）；
 *           429 按 retry-after 退避；退避/故障期间展示 ≤15 分钟内的旧值并带 `*`。
 *
 * NAS / 手机看板为可选项，密钥不入库；在 ~/.swiftbar-support/usage-monitor.json 配置:
 *   {"nasUrl":"http://<NAS_IP>:8787","nasKey":"<X-Token>","dashboardUrl":"https://.../usage/?k=..."}
 */
'use strict';
// SwiftBar 开机自启时 PATH 被精简，找不到 node/codex 会整条消失，这里写死补全
process.env.PATH = ['/opt/homebrew/bin', '/usr/local/bin', '/usr/bin', '/bin', '/usr/sbin', '/sbin', process.env.PATH || ''].join(':');

const { spawn, execFileSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const HOME = os.homedir();
const CACHE_FILE = path.join(HOME, '.swiftbar', '.claude_usage_cache.json');
const CFG_FILE = path.join(HOME, '.swiftbar-support', 'usage-monitor.json');
const CLAUDE_TTL_MS = 90 * 1000;        // 去重缓存，必须 < 刷新间隔(2m)
const STALE_MAX_MS = 15 * 60 * 1000;    // 故障时最多把 15 分钟内的旧值当展示值（带 *）
const NAS_FRESH_MS = 4 * 60 * 1000;     // 借用 NAS 数据的新鲜度要求
const UA = 'claude-code/2.1.81';        // ⚠️ 别改：非 claude-code UA 有专门的死桶限流

// ---------- 小工具 ----------

const num = (v) => {
  if (typeof v === 'number' && isFinite(v)) return v;
  if (typeof v === 'string' && v.trim() !== '' && isFinite(+v)) return +v;
  return null;
};

function resetDate(x) {
  for (const k of ['resets_at', 'resetsAt', 'reset_at', 'resetAt', 'resets']) {
    const v = x[k];
    if (v == null) continue;
    if (typeof v === 'number') return new Date(v > 1e12 ? v : v * 1000);
    const d = new Date(v);
    if (!isNaN(d)) return d;
  }
  const s = num(x.resets_in_seconds ?? x.resetsInSeconds);
  if (s != null) return new Date(Date.now() + s * 1000);
  return null;
}

const pad = (n) => String(n).padStart(2, '0');
const hhmm = (d) => `${pad(d.getHours())}:${pad(d.getMinutes())}`;

function fmtReset(d) {
  if (!d) return '';
  const now = new Date();
  return d.toDateString() === now.toDateString()
    ? `今天 ${hhmm(d)} 重置`
    : `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${hhmm(d)} 重置`;
}

const colorRem = (r) => (r <= 10 ? 'red' : r <= 30 ? 'orange' : 'green');

function httpJson(url, headers, timeoutMs) {
  return new Promise((resolve) => {
    let lib;
    try { lib = url.startsWith('https') ? require('https') : require('http'); }
    catch (_) { return resolve({ status: 0 }); }
    const req = lib.request(url, { method: 'GET', headers, timeout: timeoutMs }, (res) => {
      let body = '';
      res.on('data', (d) => (body += d));
      res.on('end', () => {
        let json = null;
        try { json = JSON.parse(body); } catch (_) {}
        resolve({ status: res.statusCode, headers: res.headers, json });
      });
    });
    req.on('timeout', () => { req.destroy(); resolve({ status: 0 }); });
    req.on('error', () => resolve({ status: 0 }));
    req.end();
  });
}

function loadJson(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch (_) { return {}; }
}

function saveCache(obj) {
  try {
    fs.mkdirSync(path.dirname(CACHE_FILE), { recursive: true });
    fs.writeFileSync(CACHE_FILE, JSON.stringify(obj));
  } catch (_) {}
}

// 在任意 JSON 里递归收集「用量窗口」候选，并挑出 5h / 周 两个窗口
function collectWindows(node, out = [], keyPath = '') {
  if (!node || typeof node !== 'object') return out;
  if (Array.isArray(node)) {
    node.forEach((v, i) => collectWindows(v, out, `${keyPath}[${i}]`));
    return out;
  }
  const used = num(node.used_percent ?? node.usedPercent ?? node.utilization);
  const rem = num(node.remaining_percent ?? node.remainingPercent ?? node.percentRemaining);
  if (used != null || rem != null) {
    out.push({
      remaining: Math.max(0, Math.min(100, rem != null ? rem : 100 - used)),
      resetAt: resetDate(node),
      minutes: num(node.window_minutes ?? node.windowMinutes),
      key: keyPath.toLowerCase(),
    });
  }
  for (const [k, v] of Object.entries(node)) {
    if (v && typeof v === 'object') collectWindows(v, out, `${keyPath}.${k}`);
  }
  return out;
}

function pickPair(wins) {
  const is5h = (w) => (w.minutes != null ? w.minutes <= 360 : /five|5h|primary|session/.test(w.key));
  const isWk = (w) => (w.minutes != null ? w.minutes >= 6000 : /seven|7d|week|secondary/.test(w.key));
  const five = wins.find(is5h) || null;
  const week = wins.find((w) => w !== five && isWk(w)) || null;
  if (!five && !week) return null;
  return { fiveHour: five, weekly: week };
}

function findEntry(node, want) {
  if (!node || typeof node !== 'object') return null;
  if (Array.isArray(node)) {
    for (const v of node) { const r = findEntry(v, want); if (r) return r; }
    return null;
  }
  if (String(node.provider || node.name || '').toLowerCase().includes(want)) return node;
  if (node[want] && typeof node[want] === 'object') return node[want];
  for (const v of Object.values(node)) {
    if (v && typeof v === 'object') { const r = findEntry(v, want); if (r) return r; }
  }
  return null;
}

// ---------- Codex ----------

function codexAppServer(timeoutMs = 15000) {
  return new Promise((resolve) => {
    let p;
    try { p = spawn('codex', ['app-server'], { stdio: ['pipe', 'pipe', 'ignore'] }); }
    catch (_) { return resolve(null); }
    let buf = '';
    let done = false;
    const finish = (v) => { if (done) return; done = true; try { p.kill(); } catch (_) {} resolve(v); };
    const timer = setTimeout(() => finish(null), timeoutMs);
    p.on('error', () => { clearTimeout(timer); finish(null); });
    p.on('exit', () => setTimeout(() => finish(null), 50));
    p.stdout.on('data', (d) => {
      buf += d;
      let idx;
      while ((idx = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, idx).trim();
        buf = buf.slice(idx + 1);
        if (!line) continue;
        let msg;
        try { msg = JSON.parse(line); } catch (_) { continue; }
        if (msg.id === 1) {
          p.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'initialized' }) + '\n');
          p.stdin.write(JSON.stringify({ jsonrpc: '2.0', id: 2, method: 'account/rateLimits/read' }) + '\n');
        } else if (msg.id === 2) {
          clearTimeout(timer);
          finish(msg.result || null);
        }
      }
    });
    try {
      p.stdin.write(JSON.stringify({
        jsonrpc: '2.0', id: 1, method: 'initialize',
        params: { clientInfo: { name: 'swiftbar-usage', title: 'SwiftBar usage', version: '2.0.0' } },
      }) + '\n');
    } catch (_) { clearTimeout(timer); finish(null); }
  });
}

function codexbarProvider(want) {
  let out;
  try {
    out = execFileSync('codexbar', ['usage', '--provider', want, '--source', 'auto', '--format', 'json'],
      { encoding: 'utf8', timeout: 20000 });
  } catch (_) { return null; }
  try {
    const json = JSON.parse(out);
    const entry = findEntry(json, want) || json;
    const pair = pickPair(collectWindows(entry));
    if (!pair) return null;
    const src = typeof entry.source === 'string' ? ` · ${entry.source}` : '';
    return { ...pair, source: `CodexBar${src}` };
  } catch (_) { return null; }
}

async function getCodex() {
  const res = await codexAppServer();
  if (res) {
    const rl = res.rateLimits || res.rate_limits || res;
    const wins = collectWindows({ primary: rl.primary, secondary: rl.secondary });
    const pair = wins.length ? pickPair(wins) : null;
    if (pair) return { ...pair, source: 'app-server' };
  }
  const cb = codexbarProvider('codex');
  if (cb) return cb;
  return { error: '未取到 Codex 限额：确认已装 codex 并用 ChatGPT 账号登录（codex login；API key 模式读不到限额）' };
}

// ---------- Claude ----------

function claudeToken() {
  try {
    const out = execFileSync('security', ['find-generic-password', '-s', 'Claude Code-credentials', '-w'],
      { encoding: 'utf8', timeout: 5000 });
    const j = JSON.parse(out.trim());
    if (j.claudeAiOauth) return j.claudeAiOauth;
  } catch (_) {}
  try {
    return loadJson(path.join(HOME, '.claude', '.credentials.json')).claudeAiOauth || null;
  } catch (_) { return null; }
}

async function claudeFromOauth() {
  const tok = claudeToken();
  if (!tok || !tok.accessToken) return { error: '未找到 Claude Code 登录凭证（钥匙串 / ~/.claude/.credentials.json）' };
  const r = await httpJson('https://api.anthropic.com/api/oauth/usage', {
    Authorization: `Bearer ${tok.accessToken}`,
    'anthropic-beta': 'oauth-2025-04-20',
    'User-Agent': UA,
  }, 10000);
  if (r.status === 200 && r.json) {
    const w = (k) => {
      const it = r.json[k];
      if (!it || it.utilization == null) return null;
      return { remaining: Math.max(0, 100 - it.utilization), resetAt: resetDate(it) };
    };
    const result = { fiveHour: w('five_hour'), weekly: w('seven_day'), source: 'OAuth' };
    if (result.fiveHour || result.weekly) return { result };
    return { error: 'usage 接口返回了未知格式' };
  }
  if (r.status === 401) return { error: 'token 过期：打开 Claude Code 用一次（claude -p hi）；长期没用则 /login' };
  if (r.status === 429) {
    const ra = parseInt(r.headers['retry-after'] || '0', 10) || 300;
    return { blockUntil: Date.now() + ra * 1000, error: `被限流(429)，约 ${Math.round(ra / 60)} 分钟后自动重试` };
  }
  return { error: `usage 接口异常（HTTP ${r.status || '网络失败'}）` };
}

async function claudeFromNas(cfg) {
  if (!cfg.nasUrl || !cfg.nasKey) return null;
  const r = await httpJson(`${cfg.nasUrl}/data?k=${encodeURIComponent(cfg.nasKey)}`,
    { 'X-Token': cfg.nasKey }, 3000);
  if (r.status !== 200 || !r.json) return null;
  const entries = Array.isArray(r.json) ? r.json : Object.values(r.json);
  for (const e of entries) {
    if (!e || typeof e !== 'object' || !e.claude) continue;
    const ts = num(e.ts ?? e.timestamp ?? e.updated_at);
    const tsMs = ts == null ? NaN : (ts > 1e12 ? ts : ts * 1000);
    if (!(Date.now() - tsMs <= NAS_FRESH_MS)) continue;
    const pair = pickPair(collectWindows(e.claude));
    if (pair) return { ...pair, source: `NAS · ${e.machine || e.name || '其他机器'}` };
  }
  return null;
}

// 缓存经 JSON 序列化后 resetAt 变成字符串，读回时还原成 Date
function reviveCached(r) {
  if (!r || typeof r !== 'object') return r;
  for (const k of ['fiveHour', 'weekly']) {
    if (r[k] && typeof r[k].resetAt === 'string') {
      const d = new Date(r[k].resetAt);
      r[k] = { ...r[k], resetAt: isNaN(d) ? null : d };
    }
  }
  return r;
}

function staleOr(cache, now, errMsg) {
  if (cache.claude && now - cache.ts < STALE_MAX_MS) {
    return { ...cache.claude, stale: true, staleAge: Math.max(1, Math.round((now - cache.ts) / 60000)), note: errMsg };
  }
  return { error: errMsg };
}

async function getClaude(cfg) {
  const now = Date.now();
  const cache = loadJson(CACHE_FILE);
  if (cache.claude) cache.claude = reviveCached(cache.claude);
  if (cache.claude && now - cache.ts < CLAUDE_TTL_MS) return cache.claude; // 90s 去重
  if (cache.blockUntil && now < cache.blockUntil) {
    const left = Math.ceil((cache.blockUntil - now) / 60000);
    return staleOr(cache, now, `限流退避中，约 ${left} 分钟后自动重试（别删缓存硬催，会加长惩罚）`);
  }
  let r = codexbarProvider('claude');
  if (!r) r = await claudeFromNas(cfg);
  let err = null;
  if (!r) {
    const o = await claudeFromOauth();
    if (o.result) r = o.result;
    else {
      err = o.error;
      if (o.blockUntil) {
        saveCache({ ...cache, blockUntil: o.blockUntil });
        return staleOr(cache, now, o.error);
      }
    }
  }
  if (r) { saveCache({ ts: now, claude: r }); return r; }
  return staleOr(cache, now, err || '所有数据源都失败');
}

// ---------- 输出 ----------

const lines = [];
const L = (s) => lines.push(s);

function titleSeg(label, r) {
  if (!r || r.error) return `${label} ?`;
  const p = (w) => (w ? `${Math.round(w.remaining)}%` : '--');
  let s = `${label} ${p(r.fiveHour)}/${p(r.weekly)}`;
  if (r.stale) s += '*';
  if (r.fiveHour && r.fiveHour.resetAt) s += ` ⇢${hhmm(r.fiveHour.resetAt)}`;
  return s;
}

function section(name, r) {
  L(`${name} | size=13`);
  if (!r || r.error) {
    L(`${(r && r.error) || '无数据'} | color=gray size=12`);
    return;
  }
  const row = (label, w) => {
    if (!w) return;
    const reset = w.resetAt ? `（${fmtReset(w.resetAt)}）` : '';
    L(`${label} 剩余 ${Math.round(w.remaining)}%${reset} | color=${colorRem(w.remaining)} font=Menlo size=12`);
  };
  row('5 小时', r.fiveHour);
  row('7 天', r.weekly);
  if (r.stale) L(`* 缓存数据（${r.staleAge} 分钟前）：${r.note || ''} | color=gray size=11`);
  if (r.source) L(`来源：${r.source} | color=gray size=11`);
}

async function main() {
  const cfg = loadJson(CFG_FILE);
  const [codex, claude] = await Promise.all([getCodex(), getClaude(cfg)]);
  L(`${titleSeg('Cdx', codex)} ${titleSeg('Cld', claude)}`);
  L('---');
  section('Codex', codex);
  L('---');
  section('Claude', claude);
  L('---');
  if (cfg.dashboardUrl) L(`手机看板 | href=${cfg.dashboardUrl}`);
  L('刷新 | refresh=true');
  console.log(lines.join('\n'));
}

main().catch((e) => {
  console.log('Cdx ? Cld ?');
  console.log('---');
  console.log(`脚本异常：${String(e && e.message ? e.message : e)} | color=red size=12`);
});
