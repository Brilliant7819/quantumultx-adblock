#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantumultX 广告资源自动生成器 (v2 · 多源聚合)
================================================
每天定时拉取多个上游广告资源，聚合去重，生成：
  - dist/splash-killer.list     分流层（HOST-SUFFIX / HOST / HOST-KEYWORD / REJECT）
  - dist/adblock-splash.conf    开屏广告重写（含自动 hostname 行）
  - dist/adblock-feed.conf      信息流/弹窗广告重写（含自动 hostname 行）
  - dist/adblock-script.conf    脚本层去广告（引用本仓库 splash-killer.js）
  - dist/splash-killer.js       脚本本体（从上游复制，保证可用）
  - dist/feed-killer.js         脚本本体
  - dist/README.md              使用说明 + 时间戳 + 统计

上游源（多源聚合，可在线访问的才会合并，死链自动跳过）：
  - anti-AD            ~10 万条广告域名（每日更新，最强覆盖）
  - hwind2021          Splash-Killer 开屏 SDK + 重写规则 + 脚本
  - NobyDa             AdRule.list 补充广告域名

用法：
  python generator.py                 # 全部生成
  python generator.py --check-only    # 只检测上游可达性，不写文件
"""
import re
import sys
import time
import json
import urllib.request
import urllib.error
from pathlib import Path
from collections import OrderedDict

OUT = Path(__file__).parent / "dist"

# ========== 多源上游定义 ==========
# 分流域名源：返回域名集合
FILTER_SOURCES = {
    "anti-ad-quanx": "https://raw.githubusercontent.com/privacy-protection-tools/anti-AD/master/anti-ad-quanx.txt",
    "anti-ad-surge": "https://raw.githubusercontent.com/privacy-protection-tools/anti-AD/master/anti-ad-surge.txt",
    "nobyda-adrule": "https://raw.githubusercontent.com/NobyDa/Script/master/QuantumultX/AdRule.list",
    "hwind-splash-killer": "https://raw.githubusercontent.com/hwind2021/QuantumultX-AdBlock-CN/main/quantumultx/filter/Splash-Killer.list",
    "hwind-antihijack": "https://raw.githubusercontent.com/hwind2021/QuantumultX-AdBlock-CN/main/quantumultx/filter/AdBlock-AntiHijack.list",
    "hwind-privacy": "https://raw.githubusercontent.com/hwind2021/QuantumultX-AdBlock-CN/main/quantumultx/filter/AdBlock-Privacy.list",
    "hwind-blockhttpdns": "https://raw.githubusercontent.com/hwind2021/QuantumultX-AdBlock-CN/main/quantumultx/filter/BlockHttpDNS.list",
    # 国际源（Adblock Plus 语法 ||domain^）
    "easylistchina": "https://raw.githubusercontent.com/easylist/easylistchina/master/easylistchina.txt",
    "easylist-intl": "https://easylist.to/easylist/easylist.txt",
    "easyprivacy": "https://easylist.to/easylist/easyprivacy.txt",
    "adguard-base": "https://filters.adtidy.org/extension/ublock/filters/1.txt",
    "adguard-mobile": "https://filters.adtidy.org/extension/ublock/filters/11.txt",
    "adguard-annoyance": "https://filters.adtidy.org/extension/ublock/filters/14.txt",
    "adguard-social": "https://filters.adtidy.org/extension/ublock/filters/2.txt",
    "adguard-tracking": "https://filters.adtidy.org/extension/ublock/filters/3.txt",
    "adguard-gaming": "https://filters.adtidy.org/extension/ublock/filters/15.txt",
    "adguard-chinese": "https://filters.adtidy.org/extension/ublock/filters/224.txt",
    "adguard-annoyance2": "https://filters.adtidy.org/extension/ublock/filters/6.txt",
    "adguard-tracking-servers": "https://filters.adtidy.org/extension/ublock/filters/17.txt",
    # hosts 格式源（0.0.0.0 domain / 127.0.0.1 domain）
    "stevenblack": "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
    "1hosts": "https://raw.githubusercontent.com/badmojr/1Hosts/master/Lite/hosts.txt",
    "peterlowe": "https://pgl.yoyo.org/adservers/serverlist.php?hostformat=hosts&showintro=0&mimetype=plaintext",
}

# 这些源用 ABP 语法解析（||domain^），其余用 parse_domains
ABP_SOURCES = {"easylistchina", "easylist-intl", "easyprivacy", "adguard-base", "adguard-mobile",
               "adguard-annoyance", "adguard-social", "adguard-tracking", "adguard-gaming",
               "adguard-chinese", "adguard-annoyance2", "adguard-tracking-servers"}

# 这些源是 hosts 格式（0.0.0.0 domain / 127.0.0.1 domain），用 parse_hosts
HOSTS_SOURCES = {"stevenblack", "1hosts", "peterlowe"}

# 重写层源：返回原始规则文本（末尾自动补 hostname）
REWRITE_SOURCES = {
    "adblock_splash": "https://raw.githubusercontent.com/hwind2021/QuantumultX-AdBlock-CN/main/quantumultx/rewrite/AdBlock-Splash.conf",
    "adblock_feed": "https://raw.githubusercontent.com/hwind2021/QuantumultX-AdBlock-CN/main/quantumultx/rewrite/AdBlock-Feed.conf",
}

# 脚本层源
SCRIPT_SOURCES = {
    "adblock_script": "https://raw.githubusercontent.com/hwind2021/QuantumultX-AdBlock-CN/main/quantumultx/rewrite/AdBlock-Script.conf",
}

# 脚本本体
SCRIPTS = {
    "splash-killer.js": "https://raw.githubusercontent.com/hwind2021/QuantumultX-AdBlock-CN/main/quantumultx/script/splash-killer.js",
    "feed-killer.js": "https://raw.githubusercontent.com/hwind2021/QuantumultX-AdBlock-CN/main/quantumultx/script/feed-killer.js",
}

# ========== 解锁模块（破解功能脚本，远程引用，每日验证可达性，死链自动剔除）==========
# sooyaaabo/Egern 45 个
UNLOCK_SOOYA = {
    "RevenueCat": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/RevenueCat.module",
    "Bilibili": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/Bilibili.module",
    "QQMusic": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/QQMusic.module",
    "NeteaseMusic": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/NeteaseMusic.module",
    "Spotify": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/Spotify.module",
    "KuwoMusic": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/KuwoMusic.module",
    "YoukuVideo": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/YoukuVideo.module",
    "IQIYI": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/IQIYI.module",
    "MangoTV": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/MangoTV.module",
    "HimalayaFM": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/HimalayaFM.module",
    "Zhihu": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/Zhihu.module",
    "RedNote": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/RedNote.module",
    "Keep": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/Keep.module",
    "Fenbi": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/Fenbi.module",
    "Railway12306": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/Railway12306.module",
    "DiDi": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/DiDi.module",
    "QuarkBrowser": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/QuarkBrowser.module",
    "ThunderCloudDisk": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/ThunderCloudDisk.module",
    "BodianMusic": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/BodianMusic.module",
    "SodaMusic": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/SodaMusic.module",
    "Listenify": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/Listenify.module",
    "VVebo": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/VVebo.module",
    "Weibo": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/Weibo.module",
    "Soul": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/Soul.module",
    "LuckinCoffee": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/LuckinCoffee.module",
    "Cainiao": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/Cainiao.module",
    "Alipan": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/Alipan.module",
    "BaiduTieba": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/BaiduTieba.module",
    "ColorfulCloudsWeatherPro": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/ColorfulCloudsWeatherPro.module",
    "QQ": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/QQ.module",
    "IThome": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/IThome.module",
    "HUPU": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/HUPU.module",
    "Ezviz": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/Ezviz.module",
    "Fanshu": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/Fanshu.module",
    "KDocs": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/KDocs.module",
    "ChinaMobile": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/ChinaMobile.module",
    "ChinaUnicom": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/ChinaUnicom.module",
    "Bank": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/Bank.module",
    "Amap": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/Amap.module",
    "Goofish": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/Goofish.module",
    "smzdm": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/smzdm.module",
    "iTunes": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/iTunes.module",
    "Google": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/Google.module",
    "YouTube": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/YouTube.module",
    "AppRaven": "https://github.com/sooyaaabo/Egern/raw/refs/heads/main/Module/AppRaven.module",
}

# BOBOLAOSHIV 20 个
UNLOCK_BOBOLA = {
    "AdGuard": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/AdGuard/AdGuard.conf",
    "Audiomack": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/Audiomack/Audiomack.conf",
    "Boom": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/Boom/Boom.conf",
    "FilmicPro": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/FilmicPro/FilmicPro.conf",
    "Filmix": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/Filmix/Filmix.conf",
    "IFTTT": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/IFTTT/IFTTT.conf",
    "LeicaLUX": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/LeicaLUX/LeicaLUX.conf",
    "MIX": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/MIX/MIX.conf",
    "MuBu": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/MuBu/MuBu.conf",
    "Notability": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/Notability/Notability.conf",
    "Perfect365": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/Perfect365/Perfect365.conf",
    "Photomator": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/Photomator/Photomator.conf",
    "ProCamera": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/ProCamera/ProCamera.conf",
    "Snailsleep": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/Snailsleep/Snailsleep.conf",
    "WPS": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/WPS/WPS.conf",
    "iLovePDF": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/iLovePDF/iLovePDF.conf",
    "GunDongJiePing": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/GunDongJiePing/GunDongJiePing.conf",
    "Picsart": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/Picsart/Picsart.conf",
    "CamScanner": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/CamScanner/CamScanner.conf",
    "Goodnotes6": "https://raw.githubusercontent.com/BOBOLAOSHIV587/Rules/main/JS/Goodnotes6/Goodnotes6.conf",
}

# 平铺 QX 格式解锁/去广告模块（无 [rewrite_local] 头，直接收集所有 " url " 行）
UNLOCK_QX_FLAT = {
    # app2smile（应用去广告/解锁，QX 格式）
    "app2smile-spotify": "https://raw.githubusercontent.com/app2smile/rules/master/module/spotify.conf",
    "app2smile-bilibili": "https://raw.githubusercontent.com/app2smile/rules/master/module/bilibili-qx.conf",
    "app2smile-zhihu": "https://raw.githubusercontent.com/app2smile/rules/master/module/zhihu.conf",
    "app2smile-qidian": "https://raw.githubusercontent.com/app2smile/rules/master/module/qidian.conf",
    "app2smile-qqnews": "https://raw.githubusercontent.com/app2smile/rules/master/module/qqnews.conf",
    "app2smile-tieba": "https://raw.githubusercontent.com/app2smile/rules/master/module/tieba-qx.conf",
    "app2smile-vgtime": "https://raw.githubusercontent.com/app2smile/rules/master/module/vgtime.conf",
    "app2smile-youtube": "https://raw.githubusercontent.com/app2smile/rules/master/module/youtube-qx.conf",
    "app2smile-adsense": "https://raw.githubusercontent.com/app2smile/rules/master/module/adsense.conf",
    # NobyDa（去广告/VIP，QX 格式，无 section 头）
    "nobyda-js": "https://raw.githubusercontent.com/NobyDa/Script/master/QuantumultX/Js.conf",
    "nobyda-testflight": "https://raw.githubusercontent.com/NobyDa/Script/master/QuantumultX/TestFlightDownload.conf",
}


def surge_rule_to_qx(line):
    """把 Surge 的 [Script] / [URL Rewrite] 规则行转成 QX rewrite 规则。
    返回 (qx_line, ok)。
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None, False
    # 去掉 "名称 = " 前缀（名称可能含中文/{{{}}}，以 type= 或 pattern= 结尾才处理）
    m = re.match(r"^(.+?)\s*=\s*(type=.*)$", line)
    if m:
        line = m.group(2)
    # 去掉 {{{...}}} 占位符
    line = re.sub(r"\{\{\{[^}]*\}\}\}", "", line)
    m_type = re.search(r"type=(http-request|http-response)", line)
    m_pat = re.search(r"pattern=([^,]+)", line)
    m_script = re.search(r"script-path=([^,\s]+)", line)
    if not m_type or not m_pat or not m_script:
        return None, False
    typ = m_type.group(1)
    pat = m_pat.group(1).strip()
    script = m_script.group(1).strip()
    qx_type = {"http-request": "script-request-body", "http-response": "script-response-body"}.get(typ)
    if not qx_type:
        return None, False
    # 清理 pattern：去掉尾随无意义 ? 和悬空转义反斜杠（skin\? → skin\ 的残留 \，会使解析器报 invalid Line）
    pat = pat.rstrip("?").strip()
    pat = re.sub(r"\\+$", "", pat).strip()
    return f"{pat} url {qx_type} {script}", True


def surge_rewrite_reject_to_qx(line):
    """把 Surge [URL Rewrite] 的 reject 规则转 QX reject。"""
    line = line.strip()
    if not line or line.startswith("#"):
        return None, False
    m = re.match(r"^(.+?)\s*=\s*(.*)$", line)
    body = m.group(2) if m else line
    body = re.sub(r"\{\{\{[^}]*\}\}\}", "", body)
    m_pat = re.search(r"pattern=([^,]+)", body)
    if not m_pat:
        return None, False
    if "reject" in body.lower():
        pat = m_pat.group(1).strip().rstrip("?").strip()
        pat = re.sub(r"\\+$", "", pat).strip()
        return f"{pat} url reject", True
    return None, False


KNOWN_SECTIONS = {
    "script", "url rewrite", "rule", "mitm", "map local", "body rewrite", "header rewrite",
    "local dns", "host", "general", "rewrite", "rewrite local", "rewrite remote",
    "replication", "script", "task", "filter remote", "filter local",
    # 下划线变体（QX 原生）
    "rewrite_local", "rewrite_remote", "filter_local", "filter_remote", "task_local", "task_remote",
    "server_local", "server_remote", "http_backend", "dns", "policy",
}


def is_section(line):
    """判断一行是否为 section 头（已知 section 名，避免把 [模块名]xxx 误判）。"""
    s = line.strip()
    if not s.startswith("[") or not s.endswith("]"):
        return False
    inner = s[1:-1].strip().lower()
    return inner in KNOWN_SECTIONS


def extract_surge_mitm_hosts(text):
    """从 Surge [MITM] 提取 hostname（处理 %APPEND% 前缀，净化非法项）。"""
    hosts = set()
    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith("hostname"):
            val = line.split("=", 1)[1] if "=" in line else ""
            val = val.replace("%APPEND%", "").strip()
            for h in val.split(","):
                s = sanitize_hostname(h)
                if s:
                    hosts.add(s)
    return hosts


def extract_qx_flat(txt):
    """提取平铺 QX 重写模块的规则行 + hostname（无 [rewrite_local] 头，直接收集所有 " url " 行）。
    返回 (rules, hosts)。"""
    rules = []
    hosts = set()
    for line in txt.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if " url " in s:
            rules.append(s)
        elif s.lower().startswith("hostname"):
            val = s.split("=", 1)[1] if "=" in s else ""
            for h in val.split(","):
                s2 = sanitize_hostname(h)
                if s2:
                    hosts.add(s2)
    return rules, hosts


def gen_unlock_merged(bobola_lines, sooya_rule_lines, yqc_rule_lines, all_hosts, repo_raw):
    """合并所有解锁模块为单个 QX conf（rewrite_local + mitm hostname）。"""
    bobola_lines = clean_rewrite_rules(bobola_lines)
    sooya_rule_lines = clean_rewrite_rules(sooya_rule_lines)
    yqc_rule_lines = clean_rewrite_rules(yqc_rule_lines)
    out = [
        "# NAME: Unlock-Merged (自建聚合)",
        "# DESC: 90+ 解锁/去广告模块合并（BOBOLAOSHIV + app2smile + NobyDa + sooyaaabo + yqc007）",
        "# 由 generator.py 自动生成，QX 一键引用",
        "",
        "[rewrite_local]",
        "# ===== BOBOLAOSHIV + app2smile + NobyDa（原生 QX 格式）=====",
    ]
    out += bobola_lines
    out += ["", "# ===== sooyaaabo（Surge 转 QX）====="]
    out += sooya_rule_lines
    out += ["", "# ===== yqc007（裸脚本头部内嵌 QX 规则）====="]
    out += yqc_rule_lines
    out += ["", "[mitm]"]
    out.append("hostname = " + ", ".join(sorted(all_hosts)))
    return "\n".join(out)


# ===== yqc007 裸脚本解锁（头部内嵌 QX 规则自动提取）=====
YQC007_API = "https://api.github.com/repos/yqc007/QuantumultX/contents"
YQC007_HTML_TREE = "https://github.com/yqc007/QuantumultX/tree/master"
YQC007_RAW = "https://raw.githubusercontent.com/yqc007/QuantumultX/master/"

# QX [rewrite_local] 支持的 action 白名单（完整）。排除 Surge/Loon 专属：script-analyze-echo-response、reject-array 等。
QX_REWRITE_ACTIONS = {
    "script-request-header", "script-request-body",
    "script-response-header", "script-response-body",
    "script-error-response", "script-echo-response",
    "reject", "reject-200", "reject-403", "reject-404", "reject-406",
    "reject-408", "reject-410", "reject-451", "reject-img", "reject-dict",
    "302", "307", "request-header", "response-header",
}


KNOWN_TLDS = {
    "com", "cn", "net", "org", "io", "co", "me", "cc", "tv", "xyz", "top", "vip", "fun",
    "app", "mobi", "info", "biz", "site", "online", "tech", "store", "cloud", "dev", "pro",
    "live", "life", "world", "plus", "club", "shop", "art", "work", "news", "media", "video",
    "music", "link", "ltd", "group", "team", "space", "icu", "xin", "wang", "gov", "edu",
    "mil", "int", "asia", "fm", "im", "ly", "to", "name", "ren", "ink", "wiki", "design",
    "agency", "digital", "email", "gg", "je", "la", "vc", "ws", "pw", "tk", "nu", "run",
    "one", "two", "six", "red", "blue", "gold", "cool", "best", "love", "wine", "beer",
}

# 已知占位/垃圾域名（源模块里的占位符或明显非法碎片），直接剔除
GARBAGE_HOSTS = {
    "example.com", "example.org", "example.net",
    "localhost", "s.com", "mt.com", "tx.com", "hlw.d",
    "api.meiease", "api.picsart", "h5.you",
    "api.example.com", "www.example.com",
}


def sanitize_hostname(h):
    """净化 hostname：去端口、去错位通配符/问号、去前导 -、去纯 IP、校验真实 TLD、剔垃圾；
    返回合法域名或 None。"""
    h = (h or "").strip().lower().rstrip(".")
    if not h:
        return None
    h = re.sub(r":\d+$", "", h)  # 去端口
    if h.startswith("*."):
        body = h[2:]
        if re.fullmatch(r"[a-z0-9]([a-z0-9\-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]*[a-z0-9])?)+", body):
            if _valid_tld(body):
                return h  # 合法通配子域，保留
        return sanitize_hostname(body)
    h = h.replace("*", "").replace("?", "")  # 去错位通配符/问号
    h = h.lstrip("-")
    h = re.sub(r"\.{2,}", ".", h).strip(".")
    if not re.fullmatch(r"[a-z0-9]([a-z0-9\-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]*[a-z0-9])?)+", h):
        return None
    # 拒绝纯 IP
    if all(re.fullmatch(r"\d+", lab) for lab in h.split(".")):
        return None
    # 校验真实 TLD
    if not _valid_tld(h):
        return None
    # 剔垃圾/占位域名
    if h in GARBAGE_HOSTS:
        return None
    return h


def _valid_tld(domain):
    """校验域名最后一段是真实 TLD（2 字母 ccTLD 或已知 TLD）。"""
    last = domain.rsplit(".", 1)[-1] if "." in domain else domain
    return (len(last) == 2 and last.isalpha()) or last in KNOWN_TLDS


def _js_regex_valid(pat):
    """检查 pattern 是否为 QX/JavaScript 合法正则。
    QX 用 JS 正则引擎，不支持 (?i)/(?m) 等 PCRE 内联旗标。"""
    # 去内联旗标 (?(?i)(?m)(?s)(?x)) —— JS 不支持
    test = re.sub(r"\(\?[imsx]+\)", "", pat)
    try:
        # 用 JS 兼容的近似：Python re 校验（JS 子集）
        re.compile(test)
        return True
    except re.error:
        return False


def clean_rewrite_rules(lines):
    """过滤未知 action + 按 pattern 去重（保留第一条），用于所有 rewrite conf。
    同时剔除 QX/JS 无法编译的正则（如 (?i) 内联旗标）。"""
    out = []
    seen = set()
    for ln in lines:
        if " url " not in ln:
            out.append(ln)
            continue
        m = re.search(r"\surl\s([a-z-]+)(?:\s|$)", ln)
        if not (m and m.group(1) in QX_REWRITE_ACTIONS):
            continue  # 剔除未知 action（如 reject-array）
        pat = ln.split(" url ")[0].strip()
        pat = re.sub(r"\\+$", "", pat).strip()  # 去悬空 \
        # 去 (?i) 等 JS 不支持的内联旗标（adblock 源常见）
        pat = re.sub(r"^\(\?[imsx]+\)", "", pat).strip()
        if not _js_regex_valid(pat):
            continue  # 剔除 QX/JS 无法编译的正则
        key = re.sub(r"^\^http", "http", pat)  # 去 ^ 前缀后去重
        if key in seen:
            continue
        seen.add(key)
        rest = ln.split(" url ", 1)[1]
        out.append(pat + " url " + rest)
    return out

# 对部分正则较复杂但域名明确的模式，手动补 hostname（片段匹配）
YQC007_HOST_SUPPLEMENT = [
    (r"api_2496\.kuwo\.cn", "kuwo.cn"),
    (r"api\.(meiease|picsart)\.cn", "meiease.cn"),
    (r"api\.(meiease|picsart)\.cn", "picsart.cn"),
    (r"apiios_dq\.xiangha\.com", "xiangha.com"),
]

_YQC_DOMAIN_RE = re.compile(r"^(\*\.)?[a-z0-9]([a-z0-9\-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]*[a-z0-9])?)+$")


def _unescape(s):
    return re.sub(r"\\(.)", r"\1", s)


def _expand_alt(seg):
    """递归展开 (a|b|c) 与 (x)? 可选分组，返回所有展开变体。"""
    m = re.search(r"\(([^()]*\|[^()]*)\)", seg)
    if m:
        out = []
        for alt in m.group(1).split("|"):
            out.extend(_expand_alt(seg[:m.start()] + alt + seg[m.end():]))
        return out
    m = re.search(r"\(([^()]*)\)\?", seg)
    if m:
        inner = m.group(1)
        return (_expand_alt(seg[:m.start()] + inner + seg[m.end():])
                + _expand_alt(seg[:m.start()] + seg[m.end():]))
    return [seg]


def _trailing_literal_domain(variant):
    """取最后一个通配符(.* .+ *. )之后的字面域，净化后返回合法域名或 None。"""
    matches = list(re.finditer(r"\.\*|\.\+|\*\.", variant))
    if not matches:
        return None
    cand = variant[matches[-1].end():]
    cand = re.sub(r"^[.*+?()]+", "", cand).lstrip(".").strip(".")
    return sanitize_hostname(cand)


def extract_yqc_hosts(pat):
    """从 yqc007 URL 模式提取 hostname。
    - 纯字面域名（无通配/元字符）→ 直接添加。
    - 含 .* / .+ / *. 通配 → 提取最后一个通配符之后的字面域（→ *.domain + domain）。
    - 含 (a|b) / (x)? → 展开后逐个处理。
    只接受真实 TLD 校验通过的完整域名；拒绝 IP、垃圾碎片。
    返回 (hosts, wild_domains)。"""
    hosts = set()
    wild = set()
    s = _unescape(re.sub(r"^\^", "", pat))
    if "://" not in s:
        return hosts, wild
    seg = s.split("://", 1)[1].split("/")[0]
    seg = re.sub(r":.*$", "", seg)  # 去端口(:d{4} / :9293 / :443 等)
    for variant in _expand_alt(seg):
        variant = variant.replace("_", "")  # 下划线非合法域名字符
        # 情况A：纯字面域名（无任何通配符/元字符）
        if re.fullmatch(r"[a-z0-9.\-]+", variant):
            s2 = sanitize_hostname(variant)
            if s2:
                hosts.add(s2)
            continue
        # 情况B：含通配符/元字符 → 提取最后一个通配符之后的字面域
        s2 = _trailing_literal_domain(variant)
        if s2 and s2.count(".") >= 1:
            hosts.add("*." + s2)
            hosts.add(s2)
    return hosts, wild


def _yqc_script_list():
    """获取 yqc007 仓库的 .js 文件列表。优先 GitHub API，失败则解析 HTML tree。"""
    names = []
    try:
        data = json.loads(fetch(YQC007_API))
        names = [x["name"] for x in data if x.get("type") == "file" and x["name"].endswith(".js")]
        if names:
            return names
    except Exception:
        pass
    # 回退：解析 HTML tree（无 API 限流）
    try:
        html = fetch(YQC007_HTML_TREE)
        names = sorted(set(re.findall(r'([A-Za-z0-9._\-]+\.js)"', html)))
        if names:
            return names
    except Exception:
        pass
    return names


def extract_yqc007(existing_patterns):
    """枚举 yqc007 裸脚本，从头部提取内嵌 QX 规则 + hostname，去重。
    返回 (rules, hosts)。rules 为 [(pattern, action, script)]。"""
    rules = []
    hosts = set()
    seen = set()
    scripts = _yqc_script_list()
    for name in scripts:
        try:
            txt = fetch(YQC007_RAW + name)
        except Exception:
            continue
        for line in txt.splitlines():
            line = line.strip()
            if not (line.startswith("^") and " url script-" in line):
                continue
            parts = line.split(" url ")
            pat = parts[0].strip()
            rest = parts[1].strip()
            rp = rest.split(None, 1)
            if len(rp) != 2 or not rp[0].startswith("script-") or "https://" not in rp[1]:
                continue
            action = rp[0]
            script = rp[1].split()[0].rstrip(",").strip()
            if action not in QX_REWRITE_ACTIONS:
                continue  # 过滤非 QX 支持的 action（如 Surge 专属 script-analyze-echo-response）
            if pat in existing_patterns or pat in seen:
                continue
            # 提取 hostname；无 host 的规则无法被 MITM，跳过（避免死规则）
            hs, wl = extract_yqc_hosts(pat)
            has_supplement = any(re.search(frag, pat) for frag, _ in YQC007_HOST_SUPPLEMENT)
            if not hs and not wl and not has_supplement:
                continue
            seen.add(pat)
            rules.append((pat, action, script))
            hosts |= hs
            hosts |= {"*." + w for w in wl}
    # 手动补充 hostname
    for frag, host in YQC007_HOST_SUPPLEMENT:
        if any(re.search(frag, p) for p, _, _ in rules):
            hosts.add(host)
    return rules, hosts

# 本仓库 raw 前缀（Actions 里会被替换成真实仓库地址）
REPO_RAW = "${REPO_RAW}"


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "adblock-gen/2.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def norm(line):
    line = line.strip()
    if not line or line.startswith("#") or line.startswith("!"):
        return None
    return line


# 垃圾/假 TLD（非真实顶级域），清洗时直接剔除
FAKE_TLDS = {
    "playtop", "form", "clays", "example0101", "test", "invalid", "localhost",
    "example", "onion", "local", "home", "lan", "internal", "corp", "none",
    "bar", "foo", "host", "dummy", "fake", "sample",
}


def clean_ad_domain(d):
    """严格清洗广告域名：拒绝转义/路径垃圾、非法标签、假 TLD、纯 IP、下划线。
    返回合法域名或 None（punycode xn-- 视为合法保留）。"""
    d = (d or "").strip().lower().rstrip(".")
    if not d or "." not in d:
        return None
    # 拒绝转义/路径/下划线/通配/花括号等垃圾
    if re.search(r"[\\/{}?\[\]@_*]|\.json$|^\.|\.$", d):
        return None
    # 拒绝 hosts 文件 IP 粘连垃圾（0.0.0.0.domain / 127.0.0.1.domain）
    if re.match(r"^\d{1,3}(?:\.\d{1,3}){3}\.", d):
        return None
    # 拒绝含非域名字符
    if not re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", d):
        return None
    labels = d.split(".")
    # 拒绝以连字符开头/结尾的标签、空标签
    if any(not l or l.startswith("-") or l.endswith("-") for l in labels):
        return None
    # 拒绝假 TLD
    if labels[-1] in FAKE_TLDS:
        return None
    # 拒绝纯 IP
    if all(re.fullmatch(r"\d+", l) for l in labels):
        return None
    return d


def parse_abp_domains(text):
    """从 Adblock Plus 语法提取 ||domain^ 域名（过滤 IP、通配符、垃圾域名）。"""
    domains = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("!") or line.startswith("["):
            continue
        m = re.match(r"^\|\|([a-z0-9.-]+)\^", line.lower())
        if m:
            d = m.group(1).strip(".").lower()
            if d and "." in d and not re.match(r"^\d+(\.\d+){3}$", d) \
               and not re.search(r"[*?\[\]{}]", d) and re.search(r"[a-z]", d):
                s = clean_ad_domain(d)
                if s:
                    domains.add(s)
    return domains


def parse_domains(text):
    """从多种格式的文本中提取广告域名（兼容 QX / Surge / 通用）。"""
    domains = set()
    for line in text.splitlines():
        line = norm(line)
        if not line:
            continue
        low = line.lower()
        # 格式: host-suffix,域名,reject | domain-suffix,域名,REJECT | DOMAIN,域名 | HOST-SUFFIX,域名,REJECT
        parts = low.split(",")
        if len(parts) >= 2 and parts[0] in ("host-suffix", "domain-suffix", "host", "domain"):
            d = parts[1].strip().rstrip(".").lower()
            if d and re.search(r"[a-z0-9-]+\.[a-z]{2,}", d):
                s = clean_ad_domain(d)
                if s:
                    domains.add(s)
                continue
        # 兜底：纯域名行（含至少一个点，无路径/通配符）
        if re.match(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$", low):
            s = clean_ad_domain(low)
            if s:
                domains.add(s)
    return domains


def parse_hosts(text):
    """从 hosts 文件提取域名（0.0.0.0 domain / 127.0.0.1 domain / ::1 domain）。"""
    domains = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 去掉行内注释
        line = line.split("#")[0].strip()
        parts = line.split()
        # hosts 行: IP domain [domain2 ...]
        if len(parts) >= 2 and re.match(r"^(?:\d{1,3}(?:\.\d{1,3}){3}|::1|0:0:0:0:0:0:0:1)$", parts[0]):
            for d in parts[1:]:
                d = d.strip().lower().rstrip(".")
                if d and re.search(r"[a-z0-9-]+\.[a-z]{2,}", d):
                    s = clean_ad_domain(d)
                    if s:
                        domains.add(s)
    return domains


def extract_rewrite_hosts(text):
    """从重写规则提取显式域名（含 \. 转义处理）。"""
    hosts = set()
    for line in text.splitlines():
        line = norm(line)
        if not line:
            continue
        m = re.match(r"^(?:\^|\(\?i\))?https?\??:\/\/([^\/\s,]+)", line)
        if not m:
            continue
        h = m.group(1).replace("\\/", "/").replace("\\.", ".").replace("\\d", "d").replace("\\w", "w")
        if not re.search(r"[\[\]?*()\\{}|]", h):
            hosts.add(h.rstrip(".").lower())
    return hosts


def gen_hostname(hosts, max_len=180):
    items = sorted(hosts)
    if not items:
        return ""
    lines, cur = [], ""
    for it in items:
        if len(cur) + len(it) + 1 > max_len:
            lines.append(cur)
            cur = it
        else:
            cur = (cur + "," + it) if cur else it
    if cur:
        lines.append(cur)
    return "hostname = " + ",\n".join(lines)


def gen_hostname_single(hosts):
    """单行 hostname（QX 原生解析把多行 hostname 续行误判为 rewrite 规则）。"""
    items = sorted(hosts)
    if not items:
        return ""
    return "hostname = " + ",".join(items)


def gen_splash_list(all_domains):
    """分流层：聚合域名生成 HOST-SUFFIX/REJECT 规则（先剔除子域名冗余）。"""
    out = [
        "# NAME: Splash-Killer (自建多源聚合)",
        "# POLICY: REJECT",
        "# 由 generator.py 自动生成，含 anti-AD / hwind2021 / NobyDa / AdGuard全系 / EasyList / StevenBlack 等聚合",
        "",
    ]
    minimized = minimize_domains(all_domains)
    for d in sorted(minimized):
        out.append(f"HOST-SUFFIX,{d},REJECT")
    return "\n".join(out)


def minimize_domains(domains):
    """剔除子域名冗余：若某域名是集合中另一域名的子域名，则剔除。
    （HOST-SUFFIX 父域名会匹配所有子域，保留子域名属于重复，零覆盖损失。）"""
    dset = set(domains)
    keep = set()
    for d in dset:
        parent = d
        redundant = False
        while True:
            idx = parent.find(".")
            if idx == -1:
                break
            parent = parent[idx + 1:]
            if parent in dset:
                redundant = True
                break
        if not redundant:
            keep.add(d)
    return keep


def gen_rewrite(text, name, desc, hosts):
    out = [f"# NAME: {name}", f"# DESC: {desc}", "# 由 generator.py 自动生成，含 hostname", ""]
    seen = set()
    raw_lines = []
    for line in text.splitlines():
        line = norm(line)
        if not line:
            continue
        if line not in seen:
            seen.add(line)
            raw_lines.append(line)
    out += clean_rewrite_rules(raw_lines)
    hn = gen_hostname_single(hosts)
    if hn:
        out.append("")
        out.append(hn)
    return "\n".join(out)


def gen_script_conf(text, repo_raw):
    out = [
        "# NAME: AdBlock-Script (自建多源聚合)",
        "# DESC: JS 脚本去广告，引用本仓库脚本",
        "# 由 generator.py 自动生成",
        "",
    ]
    for line in text.splitlines():
        line = norm(line)
        if not line:
            continue
        line = re.sub(r"https?:\/\/[^\s]+\.js", f"{repo_raw}/splash-killer.js", line)
        out.append(line)
    return "\n".join(out)


def main():
    check_only = "--check-only" in sys.argv
    all_ok = True

    # 1) 拉取全部分流域名源
    print("== 分流域名源 ==")
    domain_pool = set()
    src_detail = []
    raw_filter = {}
    for name, url in FILTER_SOURCES.items():
        try:
            txt = fetch(url)
            raw_filter[name] = txt
            if name in ABP_SOURCES:
                ds = parse_abp_domains(txt)
            elif name in HOSTS_SOURCES:
                ds = parse_hosts(txt)
            else:
                ds = parse_domains(txt)
            domain_pool |= ds
            src_detail.append(f"{name}:{len(ds)}")
            print(f"  [OK] {name}: {len(ds)} 域名")
        except Exception as e:
            all_ok = False
            print(f"  [FAIL] {name}: {e}")
    print(f"  → 分流域名去重合计: {len(domain_pool)}")
    # 剔除子域名冗余（父域名 HOST-SUFFIX 已覆盖子域，零覆盖损失）
    domain_pool = minimize_domains(domain_pool)
    print(f"  → 子域名冗余剔除后: {len(domain_pool)}")

    # 2) 拉取重写层
    print("== 重写层源 ==")
    rew_raw = {}
    for name, url in REWRITE_SOURCES.items():
        try:
            rew_raw[name] = fetch(url)
            print(f"  [OK] {name}: {len(rew_raw[name])} bytes")
        except Exception as e:
            all_ok = False
            rew_raw[name] = ""
            print(f"  [FAIL] {name}: {e}")

    # 3) 拉取脚本层
    print("== 脚本层源 ==")
    scr_raw = {}
    for name, url in SCRIPT_SOURCES.items():
        try:
            scr_raw[name] = fetch(url)
            print(f"  [OK] {name}: {len(scr_raw[name])} bytes")
        except Exception as e:
            all_ok = False
            scr_raw[name] = ""
            print(f"  [FAIL] {name}: {e}")

    # 4) 解锁模块同步：下载全部 → BOBOLAOSHIV(QX原生) + sooyaaabo(Surge转QX) → 合并成单个文件
    print("== 解锁模块同步(合并) ==")
    bobola_lines = []   # QX 原生规则
    sooya_rule_lines = []  # Surge 转 QX 规则
    unlock_hosts = set()  # 全部 hostname
    unlock_ok = 0
    unlock_bad = []
    # BOBOLAOSHIV：原生 QX 格式，直接提取 [rewrite_local] 规则 + hostname
    for tag, url in UNLOCK_BOBOLA.items():
        try:
            txt = fetch(url)
            in_rl = False
            for line in txt.splitlines():
                s = line.strip()
                if is_section(s):
                    in_rl = (s[1:-1].strip().lower() == "rewrite_local")
                    continue
                if in_rl and s and not s.startswith("#") and " url " in s:
                    bobola_lines.append(s)
            # 提取 hostname
            for line in txt.splitlines():
                if line.strip().lower().startswith("hostname"):
                    val = line.split("=", 1)[1] if "=" in line else ""
                    for h in val.split(","):
                        s = sanitize_hostname(h)
                        if s:
                            unlock_hosts.add(s)
            unlock_ok += 1
        except Exception as e:
            unlock_bad.append(f"{tag}")
    # app2smile + NobyDa：平铺 QX 格式，直接收集所有 " url " 行 + hostname
    for tag, url in UNLOCK_QX_FLAT.items():
        try:
            txt = fetch(url)
            rules, hosts = extract_qx_flat(txt)
            bobola_lines.extend(rules)
            unlock_hosts |= hosts
            unlock_ok += 1
            print(f"  [OK-QXFLAT] {tag}: {len(rules)} 规则 · {len(hosts)} hostname")
        except Exception as e:
            unlock_bad.append(f"{tag}")
    # sooyaaabo：Surge 格式，转 QX
    for tag, url in UNLOCK_SOOYA.items():
        try:
            txt = fetch(url)
            in_script = in_urlrewrite = False
            for line in txt.splitlines():
                s = line.strip()
                if is_section(s):
                    lower = s[1:-1].strip().lower()
                    in_script = (lower == "script")
                    in_urlrewrite = (lower == "url rewrite")
                    continue
                if in_script and s and "type=" in s:
                    qx, ok = surge_rule_to_qx(s)
                    if ok and qx:
                        sooya_rule_lines.append(qx)
                elif in_urlrewrite and s and ("reject" in s.lower()):
                    qx, ok = surge_rewrite_reject_to_qx(s)
                    if ok and qx:
                        sooya_rule_lines.append(qx)
            # 提取 MITM hostname
            unlock_hosts |= extract_surge_mitm_hosts(txt)
            unlock_ok += 1
        except Exception as e:
            unlock_bad.append(f"{tag}")
    # yqc007：裸脚本，从头部提取内嵌 QX 规则（去重）
    existing_pats = set()
    for ln in list(bobola_lines) + list(sooya_rule_lines):
        if " url " in ln:
            existing_pats.add(ln.split(" url ")[0])
    yqc_rules, yqc_hosts = extract_yqc007(existing_pats)
    yqc_rule_lines = [f"{p} url {a} {s}" for p, a, s in yqc_rules]
    unlock_hosts |= yqc_hosts
    print(f"  [合并] BOBOLAOSHIV规则 {len(bobola_lines)} 条 · sooyaaabo规则 {len(sooya_rule_lines)} 条 · yqc007规则 {len(yqc_rule_lines)} 条 · hostname {len(unlock_hosts)} 个")
    if unlock_bad:
        print(f"  [剔除] {', '.join(unlock_bad)}")

    if check_only:
        print("CHECK:", "PASS" if all_ok else "FAIL")
        return 0 if all_ok else 1

    # 4) 聚合 hostname
    #    关键取舍：分流层(splash-killer.list)可用全量 109K 域名(REJECT，无需 MITM)；
    #    但 hostname 只放"重写规则真正需要 MITM 的域名"——即重写显式域名 + 开屏SDK域名。
    #    不能把全量 anti-AD 塞进 MITM，否则 QX MITM 列表爆炸、拖慢。
    splash_rew = extract_rewrite_hosts(rew_raw.get("adblock_splash", ""))
    feed_rew = extract_rewrite_hosts(rew_raw.get("adblock_feed", ""))
    # 开屏 SDK 域名（hwind Splash-Killer 等，这些是需要 MITM 处理开屏广告的核心）
    mitm_core = parse_domains(raw_filter.get("hwind-splash-killer", "")) | parse_domains(raw_filter.get("hwind-blockhttpdns", ""))
    # hostname 集合 = 重写显式域名 + 开屏SDK域名（有限集合）
    splash_hosts = splash_rew | mitm_core
    feed_hosts = feed_rew | mitm_core

    # 5) 生成文件
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "splash-killer.list").write_text(gen_splash_list(domain_pool), encoding="utf-8")
    (OUT / "adblock-splash.conf").write_text(
        gen_rewrite(rew_raw.get("adblock_splash", ""), "AdBlock-Splash", "开屏广告重写（含自动 hostname）", splash_hosts), encoding="utf-8")
    (OUT / "adblock-feed.conf").write_text(
        gen_rewrite(rew_raw.get("adblock_feed", ""), "AdBlock-Feed", "信息流/弹窗重写（含自动 hostname）", feed_hosts), encoding="utf-8")

    repo_raw = REPO_RAW if not REPO_RAW.startswith("$") else "https://raw.githubusercontent.com/OWNER/REPO/main/script"
    (OUT / "adblock-script.conf").write_text(gen_script_conf(scr_raw.get("adblock_script", ""), repo_raw), encoding="utf-8")

    for fname, url in SCRIPTS.items():
        try:
            (OUT / fname).write_text(fetch(url), encoding="utf-8")
            print(f"  [OK] script {fname}")
        except Exception as e:
            print(f"  [FAIL] script {fname}: {e}")

    # 解锁模块合并文件（单文件，QX 一键引用）
    repo_raw2 = REPO_RAW if not REPO_RAW.startswith("$") else "https://raw.githubusercontent.com/OWNER/REPO/main/script"
    merged = gen_unlock_merged(bobola_lines, sooya_rule_lines, yqc_rule_lines, unlock_hosts, repo_raw2)
    (OUT / "unlock-merged.conf").write_text(merged, encoding="utf-8")
    print(f"  [OK] unlock-merged.conf: {unlock_ok} 模块合并 → {len(bobola_lines)+len(sooya_rule_lines)+len(yqc_rule_lines)} 条规则")

    ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    src_line = " · ".join(src_detail)
    readme = f"""# 自建 QuantumultX 广告清单（多源聚合）

> 由 GitHub Actions 每日自动生成，无需手动维护。

## 上游源（广告）
{src_line}

## 上游源（解锁模块）
- sooyaaabo/Egern: 45 个模块
- BOBOLAOSHIV587/Rules: 20 个模块
> 每日验证可达性，死链自动剔除。

## 文件
- `splash-killer.list` —— 分流层（按域名 REJECT，无需 MITM）
- `adblock-splash.conf` —— 开屏广告重写（含 hostname，opt-parser=true 自动合并）
- `adblock-feed.conf` —— 信息流/弹窗重写（含 hostname）
- `adblock-script.conf` —— 脚本层去广告（引用本仓库脚本）
- `splash-killer.js` / `feed-killer.js` —— 脚本本体
- `unlock-merged.conf` —— **全部解锁模块合并（QX 一键引用，含 hostname）**

## QX 配置
```ini
[filter_remote]
https://raw.githubusercontent.com/OWNER/REPO/main/dist/splash-killer.list, tag=自建-开屏分流, update-interval=28800, opt-parser=true, enabled=true

[rewrite_remote]
https://raw.githubusercontent.com/OWNER/REPO/main/dist/adblock-splash.conf, tag=自建-开屏重写, update-interval=28800, opt-parser=true, enabled=true
https://raw.githubusercontent.com/OWNER/REPO/main/dist/adblock-feed.conf, tag=自建-信息流重写, update-interval=28800, opt-parser=true, enabled=true
https://raw.githubusercontent.com/OWNER/REPO/main/dist/adblock-script.conf, tag=自建-脚本去广告, update-interval=28800, opt-parser=true, enabled=true
https://raw.githubusercontent.com/OWNER/REPO/main/dist/unlock-merged.conf, tag=自建-解锁模块, update-interval=86400, opt-parser=true, enabled=true
```

> `unlock-merged.conf` 为**单个文件**，内含 `[rewrite_local]` + `[mitm] hostname`，QX 用 `opt-parser=true` 一键引用即可，无需手动复制。

## 解锁模块
{unlock_ok} 个模块合并（BOBOLAOSHIV QX 原生 + sooyaaabo Surge 转 QX + yqc007 裸脚本），{len(bobola_lines)} + {len(sooya_rule_lines)} + {len(yqc_rule_lines)} 条规则，hostname {len(unlock_hosts)} 个。

## 统计
- 聚合广告域名: {len(domain_pool)} 个
- 开屏重写 hostname: {len(splash_hosts)} 个
- 信息流重写 hostname: {len(feed_hosts)} 个
- 有效解锁模块: {unlock_ok} 个（合并 {len(bobola_lines)}+{len(sooya_rule_lines)}+{len(yqc_rule_lines)} 条规则）

最后生成: {ts}
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    print(f"\n完成！生成 {len(list(OUT.glob('*')))} 个文件到 dist/")
    print(f"  聚合域名 {len(domain_pool)} · 开屏 hostname {len(splash_hosts)} · 信息流 hostname {len(feed_hosts)} · 解锁模块 {unlock_ok}（{len(bobola_lines)}+{len(sooya_rule_lines)}+{len(yqc_rule_lines)} 规则）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
