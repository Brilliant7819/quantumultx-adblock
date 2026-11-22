#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""业务分流聚合：把主配置引用的第三方业务规则抓取、格式归一为 QX 原生，行内带策略，
合并进仓库单文件 dist/rules-merged.list。广告 reject 分片仍由 generator.py 维护。"""
import urllib.request, urllib.error, re, sys
from pathlib import Path

OUT = Path(__file__).parent / "dist"

# tag, url, policy, parser(qx/surge/yaml)
# 顺序即匹配优先级：专项/细分在前，大类/直连兜底在后；跨源同域名不同策略不去重。
MERGE_FILTERS = [
    ("OpenAI", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/OpenAI/OpenAI.list", "OpenAI", "qx"),
    ("Telegram", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Telegram/Telegram.list", "✉️ Telegram", "qx"),
    ("Netflix", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Netflix/Netflix.list", "📺 Netflix", "qx"),
    ("YouTube", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/YouTube/YouTube.list", "🎬 YouTube", "qx"),
    ("Google", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Google/Google.list", "美国节点", "qx"),
    ("GitHub", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/GitHub/GitHub.list", "全球加速", "qx"),
    ("Steam", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Steam/Steam.list", "全球加速", "qx"),
    ("Apple", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Apple/Apple.list", "🍎 苹果服务", "qx"),
    ("Microsoft", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Microsoft/Microsoft.list", "direct", "qx"),
    ("NeteaseMusic", "https://raw.githubusercontent.com/GeQ1an/Rules/master/QuantumultX/Filter/Optional/Netease%20Music.list", "Netease Music", "qx"),
    ("Ai.yaml", "https://gist.githubusercontent.com/ddgksf2013/cb4121e8b5c5d865cc949cb8120320c4/raw/Ai.yaml", "💻 Ai", "yaml"),
    ("TikTok", "https://raw.githubusercontent.com/ConnersHua/RuleGo/master/Surge/Ruleset/Extra/Streaming/Video/TikTok.list", "全球加速", "surge"),
    ("WeChat", "https://raw.githubusercontent.com/ConnersHua/RuleGo/master/Surge/Ruleset/Extra/WeChat.list", "direct", "surge"),
    ("Hijacking", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Hijacking/Hijacking.list", "reject", "qx"),
    ("Direct+", "https://raw.githubusercontent.com/ConnersHua/RuleGo/master/Surge/Ruleset/Direct+.list", "direct", "surge"),
    ("!CN", "https://raw.githubusercontent.com/ConnersHua/RuleGo/master/Surge/Ruleset/Extra/Streaming/!CN.list", "国际媒体", "surge"),
    ("CN", "https://raw.githubusercontent.com/ConnersHua/RuleGo/master/Surge/Ruleset/Extra/Streaming/CN.list", "港台番剧", "surge"),
    ("GlobalMedia", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/GlobalMedia/GlobalMedia.list", "💻 国外影视", "qx"),
    ("Global", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Global/Global.list", "🌏 国外网站", "qx"),
    ("Proxy", "https://raw.githubusercontent.com/ConnersHua/RuleGo/master/Surge/Ruleset/Proxy.list", "全球加速", "surge"),
    ("China", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/China/China.list", "direct", "qx"),
    ("ChinaIPs", "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/ChinaIPs/ChinaIPs.list", "direct", "qx"),
]

SURGE_TYPE = {
    "DOMAIN": "HOST", "DOMAIN-SUFFIX": "HOST-SUFFIX", "DOMAIN-KEYWORD": "HOST-KEYWORD",
    "IP-CIDR": "IP-CIDR", "IP-CIDR6": "IP6-CIDR", "GEOIP": "GEOIP",
    "USER-AGENT": "USER-AGENT", "IP-ASN": "IP-ASN",
}
QX_TYPES = {"HOST", "HOST-SUFFIX", "HOST-KEYWORD", "HOST-WILDCARD", "IP-CIDR",
            "IP6-CIDR", "IP-ASN", "GEOIP", "USER-AGENT", "URL-REGEX"}

def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "QuantumultX/1.5.3"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")

def parse_line(line, policy, parser):
    """归一为 (qx_type, value, policy) 或 None。"""
    s = line.strip()
    if not s or s.startswith("#") or s.startswith("!") or s.startswith("- "):
        if s.startswith("- "):
            s = s[2:].strip()
        else:
            return None
    if s.startswith("payload:") or s.lower().startswith("hostname"):
        return None
    parts = [p.strip() for p in s.split(",")]
    if len(parts) < 2:
        return None
    typ = parts[0].upper()
    value = parts[1].strip()
    if parser == "surge" or parser == "yaml":
        typ = SURGE_TYPE.get(typ)
        if not typ:
            return None
        pol = policy
    else:  # qx 原生：强制使用主配置登记的策略组（源文件第三段只是作者占位 tag）
        if typ not in QX_TYPES:
            return None
        pol = policy
    if not value:
        return None
    return typ, value, pol

def main():
    seen = set()
    out_lines = []
    stat = {}
    for tag, url, policy, parser in MERGE_FILTERS:
        try:
            txt = fetch(url)
        except Exception as e:
            print(f"  [FAIL] {tag}: {e}")
            stat[tag] = -1
            continue
        kept = 0
        for line in txt.splitlines():
            r = parse_line(line, policy, parser)
            if not r:
                continue
            typ, value, pol = r
            key = (typ, value.lower(), pol)
            if key in seen:
                continue
            seen.add(key)
            out_lines.append(f"{typ},{value},{pol}")
            kept += 1
        stat[tag] = kept
        print(f"  [OK] {tag}: {kept} 条 ({parser})")
    header = [
        "# NAME: Rules-Merged (自建业务分流聚合)",
        "# DESC: 22 个上游业务规则集合并，行内自带策略；QX 原生格式，opt-parser=false",
        "# 由 build_merge.py 生成；广告 reject 分片见 dist/qx/",
        "",
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rules-merged.list").write_text("\n".join(header + out_lines) + "\n", encoding="utf-8")
    print(f"\n合计 {len(out_lines)} 条 → dist/rules-merged.list")
    print(f"体积: { (OUT / 'rules-merged.list').stat().st_size } B")

if __name__ == "__main__":
    main()
