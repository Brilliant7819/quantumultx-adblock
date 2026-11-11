#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自动检索去广告源 + QX 解锁脚本源。

流程：
  1) GitHub search API 搜索候选仓库（adblock / adguard / hosts / easylist / quantumultx / unlock / rewrite）
  2) 对候选仓库用 git/trees API 拿文件树，找 filter 文件（.list/.txt/hosts）和 rewrite 文件（.conf/.module/.js）
  3) 拉取样例文件，探测格式（abp / hosts / plain / qx-filter / surge / qx-rewrite），统计域名数 / 规则数
  4) 超阈值才收录，写入 dist/sources.json（generator 自动合并）+ dist/DISCOVERED.md（人工审核清单）

已收录源记录在 dist/sources.json，重复运行时增量探测（跳过已知仓库，不重复 API 调用）。

用法：
  python discover_sources.py [--token TOKEN] [--limit N] [--force]
    --token   GitHub token（search API 认证，Actions 里用 ${{ secrets.GITHUB_TOKEN }}）
    --limit   每个查询取仓库数上限（默认 20）
    --force   忽略已收录缓存，重新全量探测
"""
import json
import re
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

OUT = Path(__file__).parent / "dist"
SOURCES_JSON = OUT / "sources.json"

# 已收录的静态源仓库（generator.py 已硬编码，自动检索跳过，避免重复收录）
KNOWN_REPOS = {
    "privacy-protection-tools/anti-AD", "NobyDa/Script", "hwind2021/QuantumultX-AdBlock-CN",
    "easylist/easylistchina", "StevenBlack/hosts", "badmojr/1Hosts",
    "BOBOLAOSHIV587/Rules", "app2smile/rules", "sooyaaabo/Egern", "yqc007/QuantumultX",
}
# 明显无关的仓库名关键词（模板/示例/测试）
EXCLUDE_RE = re.compile(r"(template|example|demo|test|sample|scaffold|starter|boilerplate|awesome-list|blog|dotfiles|nvim|vscode|oh-my|ansible|docker|kubernetes|terraform|node_modules)", re.I)

# 搜索查询：去广告 / 解锁
AD_QUERIES = [
    "adblock hosts", "adguard hosts list", "easylist adblock", "adblock list filters",
    "anti-ad", "ad hosts blocklist", "adblock quantumultx",
]
UNLOCK_QUERIES = [
    "quantumultx script", "quantumultx rewrite", "surge module script",
    "loon script rewrite", "shadowrocket script unlock",
]

# 收录阈值
AD_MIN_DOMAINS = 500
UNLOCK_MIN_RULES = 3


def fetch(url, token=None, timeout=25):
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def gh_api(url, token=None, timeout=25):
    return json.loads(fetch(url, token, timeout))


def gh_search(q, token=None, per_page=20, sort="stars"):
    url = ("https://api.github.com/search/repositories?q=" + urllib.parse.quote(q) +
           f"&sort={sort}&order=desc&per_page={per_page}")
    try:
        data = gh_api(url, token)
        return data.get("items", [])
    except Exception as e:
        print(f"  [SEARCH-FAIL] q={q}: {e}")
        return []


def gh_tree(owner, repo, token=None):
    """获取仓库文件路径列表（git/trees recursive）。失败返回空。"""
    for branch in ("main", "master"):
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        try:
            data = gh_api(url, token)
            return [t["path"] for t in data.get("tree", []) if t.get("type") == "blob"], branch
        except Exception:
            continue
    return [], None


def raw_url(owner, repo, branch, path):
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"


def probe_filter(raw):
    """探测 filter 文本格式，返回 (parser, 域名数)。"""
    abp = set(re.findall(r"^\|\|([a-z0-9.\-]+)\^", raw, re.M | re.I))
    hosts = set(re.findall(r"^0\.0\.0\.0\s+([a-z0-9.\-]+)", raw, re.M | re.I))
    hosts |= set(re.findall(r"^127\.0\.0\.1\s+([a-z0-9.\-]+)", raw, re.M | re.I))
    qx = set(re.findall(r"^HOST-SUFFIX,([a-z0-9.\-]+),", raw, re.M | re.I))
    clash = set(re.findall(r"^DOMAIN-SUFFIX,([a-z0-9.\-]+)", raw, re.M | re.I))
    if abp and len(abp) >= len(hosts) and len(abp) >= len(qx) and len(abp) >= len(clash):
        return "abp", len(abp)
    if hosts and len(hosts) >= len(qx) and len(hosts) >= len(clash):
        return "hosts", len(hosts)
    if qx and len(qx) >= len(clash):
        return "qx-filter", len(qx)
    if clash:
        return "clash", len(clash)
    return "plain", 0


def probe_unlock(raw):
    """探测 rewrite 文本格式，返回 (format, 规则数)。"""
    if re.search(r"\[Script\]", raw, re.I) and re.search(r"\[URL Rewrite\]", raw, re.I):
        return "surge", len(re.findall(r"type=(http-request|http-response)", raw))
    if re.search(r" url ", raw):
        return "qx-flat", len(re.findall(r" url ", raw))
    if re.search(r"\[\s*rewrite", raw, re.I):
        return "qx-flat", len(re.findall(r" url ", raw))
    return "unknown", 0


def candidate_filter_paths(paths):
    """从文件树里挑 filter 候选。返回 (filter_paths, rewrite_paths)。"""
    filt, rew = [], []
    for p in paths:
        low = p.lower()
        if low.endswith((".md", ".json", ".py", ".yml", ".yaml", ".xml", ".css", ".html", ".txt~")):
            continue
        if low.endswith((".conf", ".module", ".js")):
            rew.append(p)
        if low.endswith((".list", ".hosts", ".surge")) or low == "hosts":
            filt.append(p)
    return filt, rew


def discover_ad(token, limit, cached_ad, force):
    """检索去广告源。返回新增 list[dict]。"""
    found = []
    seen_repos = set()
    for q in AD_QUERIES:
        for repo in gh_search(q, token, per_page=limit):
            full = repo.get("full_name", "")
            if not full or full in KNOWN_REPOS or full in seen_repos:
                continue
            if EXCLUDE_RE.search(full):
                continue
            seen_repos.add(full)
            owner, rname = full.split("/", 1)
            paths, branch = gh_tree(owner, rname, token)
            if not paths:
                continue
            filt_paths, _ = candidate_filter_paths(paths)
            if not filt_paths:
                continue
            for fp in filt_paths[:3]:
                try:
                    raw = fetch(raw_url(owner, rname, branch, fp), token)
                except Exception:
                    continue
                parser, cnt = probe_filter(raw)
                if parser in ("abp", "hosts", "qx-filter", "plain") and cnt >= AD_MIN_DOMAINS:
                    tag = f"auto-{owner}-{rname}-{fp.split('/')[-1].split('.')[0]}".lower()
                    tag = re.sub(r"[^a-z0-9\-]+", "-", tag).strip("-")
                    if not force and any(s.get("tag") == tag for s in cached_ad):
                        continue
                    found.append({
                        "tag": tag, "type": "ad", "url": raw_url(owner, rname, branch, fp),
                        "parser": parser, "author": owner, "repo": full,
                        "file": fp, "stars": repo.get("stargazers_count", 0),
                        "domains": cnt,
                        "desc": (repo.get("description") or "")[:120],
                        "added_at": time.strftime("%Y-%m-%d", time.gmtime()),
                    })
                    print(f"  [AD+] {tag}: {parser} {cnt} 域名 ({full})")
                    break  # 每仓库收录 1 个最佳 filter 文件
    return found


def discover_unlock(token, limit, cached_unlock, force):
    """检索解锁/重写源。返回新增 list[dict]。"""
    found = []
    seen_repos = set()
    for q in UNLOCK_QUERIES:
        for repo in gh_search(q, token, per_page=limit):
            full = repo.get("full_name", "")
            if not full or full in KNOWN_REPOS or full in seen_repos:
                continue
            if EXCLUDE_RE.search(full):
                continue
            seen_repos.add(full)
            owner, rname = full.split("/", 1)
            paths, branch = gh_tree(owner, rname, token)
            if not paths:
                continue
            _, rew_paths = candidate_filter_paths(paths)
            if not rew_paths:
                continue
            for rp in rew_paths[:5]:
                try:
                    raw = fetch(raw_url(owner, rname, branch, rp), token)
                except Exception:
                    continue
                fmt, cnt = probe_unlock(raw)
                if fmt in ("surge", "qx-flat") and cnt >= UNLOCK_MIN_RULES:
                    tag = f"auto-{owner}-{rname}-{rp.split('/')[-1].split('.')[0]}".lower()
                    tag = re.sub(r"[^a-z0-9\-]+", "-", tag).strip("-")
                    if not force and any(s.get("tag") == tag for s in cached_unlock):
                        continue
                    found.append({
                        "tag": tag, "type": "unlock", "url": raw_url(owner, rname, branch, rp),
                        "format": fmt, "author": owner, "repo": full,
                        "file": rp, "stars": repo.get("stargazers_count", 0),
                        "rules": cnt,
                        "desc": (repo.get("description") or "")[:120],
                        "added_at": time.strftime("%Y-%m-%d", time.gmtime()),
                    })
                    print(f"  [UNLOCK+] {tag}: {fmt} {cnt} 规则 ({full})")
                    break  # 每仓库收录 1 个最佳 rewrite 文件
    return found


def load_cached():
    if SOURCES_JSON.exists():
        try:
            return json.loads(SOURCES_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"ad": [], "unlock": []}


def main():
    args = sys.argv[1:]
    token = None
    limit = 20
    force = False
    for i, a in enumerate(args):
        if a == "--token" and i + 1 < len(args):
            token = args[i + 1]
        elif a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
        elif a == "--force":
            force = True
    OUT.mkdir(parents=True, exist_ok=True)
    cached = load_cached()
    print(f"== 自动检索去广告源 (limit={limit}, force={force}) ==")
    new_ad = discover_ad(token, limit, cached.get("ad", []), force)
    print(f"== 自动检索解锁脚本源 (limit={limit}) ==")
    new_unlock = discover_unlock(token, limit, cached.get("unlock", []), force)

    all_ad = cached.get("ad", []) + new_ad
    all_unlock = cached.get("unlock", []) + new_unlock
    SOURCES_JSON.write_text(json.dumps({"ad": all_ad, "unlock": all_unlock}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果: 广告源 {len(all_ad)} 个（新增 {len(new_ad)}）· 解锁源 {len(all_unlock)} 个（新增 {len(new_unlock)}）")
    print(f"写入 {SOURCES_JSON}")

    # 生成人工审核清单 DISCOVERED.md
    lines = ["# 自动检索到的源（人工审核）\n",
             f"> 由 discover_sources.py 自动生成 {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}。"
             "generator 会合并 `dist/sources.json` 里已验证的源，失败自动跳过。\n"]
    lines.append("## 去广告源\n")
    for s in all_ad:
        lines.append(f"- **{s['tag']}** · {s['parser']} {s.get('domains', 0)} 域名 · 作者 `{s['author']}` · ⭐{s.get('stars', 0)}\n  - {s['url']}\n  - {s['repo']} · {s['desc']}\n")
    lines.append("## 解锁/重写源\n")
    for s in all_unlock:
        lines.append(f"- **{s['tag']}** · {s['format']} {s.get('rules', 0)} 规则 · 作者 `{s['author']}` · ⭐{s.get('stars', 0)}\n  - {s['url']}\n  - {s['repo']} · {s['desc']}\n")
    (OUT / "DISCOVERED.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"写入 {OUT / 'DISCOVERED.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
