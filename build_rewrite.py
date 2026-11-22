#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重写聚合：自建 5 conf + 可静态转换的第三方原生 QX / Surge 模块，合并进仓库单文件
dist/rewrite-merged.conf（含 [rewrite_local] 规则 + [mitm] hostname）。
不可静态合并的 SubStore / boxjs / TikTok(lookbehind) 保留在主配置单独远程引用。"""
import sys, urllib.request, re
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
sys.path.insert(0, str(ROOT))
import generator as G

# 自建 conf（本地已存在，直接并入）
SELF_REWRITES = [
    "adblock-splash.conf", "adblock-feed.conf", "adblock-script.conf",
    "unlock-merged.conf", "unlock-local.conf",
]

# 第三方原生 QX conf（extract_qx_flat 提取规则 + hostname）
NATIVE = {
    "AmapAds": "https://raw.githubusercontent.com/ddgksf2013/Rewrite/master/AdBlock/AmapAds.conf",
    "GoofishAds": "https://github.com/ddgksf2013/Rewrite/raw/master/AdBlock/GoofishAds.conf",
    "AdvertisingLite": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rewrite/QuantumultX/AdvertisingLite/AdvertisingLite.conf",
    "YoutubeAds": "https://raw.githubusercontent.com/ddgksf2013/Rewrite/master/AdBlock/YoutubeAds.conf",
    "adultraplus": "https://yfamilys.com/rewrite/adultraplus.conf",
    "Applet": "https://raw.githubusercontent.com/ddgksf2013/Rewrite/refs/heads/master/AdBlock/Applet.conf",
    "NeteaseAds": "https://raw.githubusercontent.com/ddgksf2013/Rewrite/master/AdBlock/NeteaseAds.conf",
    "Q-Search": "https://raw.githubusercontent.com/ddgksf2013/Rewrite/master/Html/Q-Search.conf",
    "UnblockURLinWeChat": "https://raw.githubusercontent.com/ddgksf2013/Rewrite/master/Function/UnblockURLinWeChat.conf",
    "NSFW": "https://github.com/amiglistimo/Quantumult-X/raw/refs/heads/main/Rewrite/NSFW.conf",
    "Cookie": "https://raw.githubusercontent.com/chavyleung/scripts/master/QuantumultX_Local_Cookie.conf",
}

# 第三方 Surge 模块（sooyaaabo/Egern）：含 [Rule] 分流 / [Map Local] / [Body Rewrite](jq) / [Script] 多段，
# 静态只能转 Script 段，Rule/Map Local/jq body 会丢功能；整体保留在主配置 opt-parser=true 远程引用，不纳入本聚合。
SURGE = {}

def read_self_conf(name):
    p = DIST / name
    if not p.exists():
        print(f"  [MISS] 自建 {name}")
        return [], set()
    txt = p.read_text(encoding="utf-8")
    rules, hosts = G.extract_qx_flat(txt)
    # 自建文件里 hostname 行已被 extract_qx_flat 收集；再从规则正则补提
    hosts |= G.extract_rewrite_hosts(txt)
    return rules, hosts

def parse_surge(txt):
    rules, hosts = [], set()
    in_script = in_urlrewrite = False
    for line in txt.splitlines():
        s = line.strip()
        if G.is_section(s):
            low = s[1:-1].strip().lower()
            in_script = (low == "script")
            in_urlrewrite = (low == "url rewrite")
            continue
        if in_script and s and "type=" in s:
            qx, ok = G.surge_rule_to_qx(s)
            if ok and qx:
                rules.append(qx)
        elif in_urlrewrite and s and "reject" in s.lower():
            qx, ok = G.surge_rewrite_reject_to_qx(s)
            if ok and qx:
                rules.append(qx)
    hosts |= G.extract_surge_mitm_hosts(txt)
    return rules, hosts

# 已下线/域名解析失效的脚本托管站（直连与本机代理均无法解析，QX 预下载脚本会报错），整站规则剔除。
# qxnav.com 等整站 TLS 异常但域名仍解析的不在此列，保留待站点恢复。
DEAD_HOSTS = {"klraw.pages.dev", "service.2ti.st"}

def drop_dead_hosts(rules):
    kept, dropped = [], 0
    for ln in rules:
        m = re.search(r"https?://([^/\s]+)", ln)
        if m and m.group(1) in DEAD_HOSTS:
            dropped += 1
            continue
        kept.append(ln)
    print(f"  [DEAD-HOST] 剔除失效托管站规则 {dropped} 条")
    return kept

def main():
    all_rules, all_hosts = [], set()
    print("== 自建 conf ==")
    for name in SELF_REWRITES:
        r, h = read_self_conf(name)
        all_rules += r
        all_hosts |= h
        print(f"  [OK] {name}: {len(r)} 规则 · {len(h)} hostname")

    print("== 第三方原生 QX ==")
    for tag, url in NATIVE.items():
        try:
            txt = G.fetch(url)
            r, h = G.extract_qx_flat(txt)
            h |= G.extract_rewrite_hosts(txt)
            all_rules += r
            all_hosts |= h
            print(f"  [OK] {tag}: {len(r)} 规则 · {len(h)} hostname")
        except Exception as e:
            print(f"  [FAIL] {tag}: {e}")

    print("== 第三方 Surge 模块 ==")
    for tag, url in SURGE.items():
        try:
            txt = G.fetch(url)
            r, h = parse_surge(txt)
            all_rules += r
            all_hosts |= h
            print(f"  [OK] {tag}: {len(r)} 规则 · {len(h)} hostname")
        except Exception as e:
            print(f"  [FAIL] {tag}: {e}")

    # 清洗：action 白名单 / 正则校验 / 去重 / 死链脚本剔除
    cleaned = G.clean_rewrite_rules(all_rules)
    cleaned = G.filter_live_scripts(cleaned)
    cleaned = drop_dead_hosts(cleaned)
    hosts = sorted({h for h in all_hosts if G.sanitize_hostname(h)})

    out = [
        "# NAME: Rewrite-Merged (自建重写聚合)",
        "# DESC: 自建开屏/信息流/脚本/解锁 + 第三方原生 QX 与 Surge 转 QX 规则合并",
        "# 由 build_rewrite.py 生成，QX 原生语法，opt-parser=false",
        "# 原作者致谢: 见 dist/CREDITS.md",
        "",
        "[rewrite_local]",
    ]
    out += cleaned
    out += ["", "[mitm]", "hostname = " + ",".join(hosts)]
    DIST.mkdir(parents=True, exist_ok=True)
    (DIST / "rewrite-merged.conf").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"\n合计 {len(cleaned)} 规则 · {len(hosts)} hostname → dist/rewrite-merged.conf")
    print(f"体积: {(DIST / 'rewrite-merged.conf').stat().st_size} B")

if __name__ == "__main__":
    main()
