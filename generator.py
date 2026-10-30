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
    "adguard-base": "https://filters.adtidy.org/extension/ublock/filters/1.txt",
    "adguard-mobile": "https://filters.adtidy.org/extension/ublock/filters/11.txt",
    "adguard-annoyance": "https://filters.adtidy.org/extension/ublock/filters/14.txt",
}

# 这些源用 ABP 语法解析（||domain^），其余用 parse_domains
ABP_SOURCES = {"easylistchina", "adguard-base", "adguard-mobile", "adguard-annoyance"}

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


def parse_abp_domains(text):
    """从 Adblock Plus 语法提取 ||domain^ 域名（过滤 IP 和通配符）。"""
    domains = set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("!") or line.startswith("["):
            continue
        m = re.match(r"^\|\|([a-z0-9.-]+)\^", line.lower())
        if m:
            d = m.group(1).strip(".").lower()
            # 过滤 IP、通配符、单标签
            if d and "." in d and not re.match(r"^\d+(\.\d+){3}$", d) \
               and not re.search(r"[*?\[\]{}]", d) and re.search(r"[a-z]", d):
                domains.add(d)
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
                domains.add(d)
                continue
        # 兜底：纯域名行（含至少一个点，无路径/通配符）
        if re.match(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$", low):
            domains.add(low)
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


def gen_splash_list(all_domains):
    """分流层：聚合域名生成 HOST-SUFFIX/REJECT 规则。"""
    out = [
        "# NAME: Splash-Killer (自建多源聚合)",
        "# POLICY: REJECT",
        "# 由 generator.py 自动生成，含 anti-AD / hwind2021 / NobyDa 聚合",
        "",
    ]
    for d in sorted(all_domains):
        out.append(f"HOST-SUFFIX,{d},REJECT")
    return "\n".join(out)


def gen_rewrite(text, name, desc, hosts):
    out = [f"# NAME: {name}", f"# DESC: {desc}", "# 由 generator.py 自动生成，含 hostname", ""]
    seen = set()
    for line in text.splitlines():
        line = norm(line)
        if not line:
            continue
        if line not in seen:
            seen.add(line)
            out.append(line)
    hn = gen_hostname(hosts)
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
            else:
                ds = parse_domains(txt)
            domain_pool |= ds
            src_detail.append(f"{name}:{len(ds)}")
            print(f"  [OK] {name}: {len(ds)} 域名")
        except Exception as e:
            all_ok = False
            print(f"  [FAIL] {name}: {e}")
    print(f"  → 分流域名去重合计: {len(domain_pool)}")

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

    # 4) 解锁模块同步：验证可达性，死链剔除，生成 rewrite_remote 配置
    print("== 解锁模块同步 ==")
    unlock_lines = []
    unlock_ok = 0
    unlock_bad = []
    for tag, url in list(UNLOCK_SOOYA.items()) + list(UNLOCK_BOBOLA.items()):
        try:
            fetch(url)  # 只验证可达
            unlock_lines.append(
                f"{url}, tag={tag}解锁, update-interval=86400, opt-parser=true, enabled=true")
            unlock_ok += 1
        except Exception as e:
            unlock_bad.append(f"{tag}")
    print(f"  [OK] 有效 {unlock_ok} · 失效剔除 {len(unlock_bad)}")
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

    # 解锁模块配置片段（rewrite_remote 行，死链已剔除）
    unlock_conf = [
        "# ===== 解锁模块（自建同步，每日验证可达性，死链自动剔除）=====",
        "# 复制到你的 [rewrite_remote] 区块",
        "",
    ] + unlock_lines
    (OUT / "unlock-rewrite.conf").write_text("\n".join(unlock_conf), encoding="utf-8")
    print(f"  [OK] unlock-rewrite.conf: {unlock_ok} 条有效模块")

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
- `unlock-rewrite.conf` —— 解锁模块配置片段（复制进 [rewrite_remote]）

## QX 配置
```ini
[filter_remote]
https://raw.githubusercontent.com/OWNER/REPO/main/dist/splash-killer.list, tag=自建-开屏分流, update-interval=28800, opt-parser=true, enabled=true

[rewrite_remote]
https://raw.githubusercontent.com/OWNER/REPO/main/dist/adblock-splash.conf, tag=自建-开屏重写, update-interval=28800, opt-parser=true, enabled=true
https://raw.githubusercontent.com/OWNER/REPO/main/dist/adblock-feed.conf, tag=自建-信息流重写, update-interval=28800, opt-parser=true, enabled=true
https://raw.githubusercontent.com/OWNER/REPO/main/dist/adblock-script.conf, tag=自建-脚本去广告, update-interval=28800, opt-parser=true, enabled=true
```

## 解锁模块（复制 unlock-rewrite.conf 内容到 [rewrite_remote]）
{unlock_ok} 个有效模块（死链已剔除）。

## 统计
- 聚合广告域名: {len(domain_pool)} 个
- 开屏重写 hostname: {len(splash_hosts)} 个
- 信息流重写 hostname: {len(feed_hosts)} 个
- 有效解锁模块: {unlock_ok} 个

最后生成: {ts}
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    print(f"\n完成！生成 {len(list(OUT.glob('*')))} 个文件到 dist/")
    print(f"  聚合域名 {len(domain_pool)} · 开屏 hostname {len(splash_hosts)} · 信息流 hostname {len(feed_hosts)} · 解锁模块 {unlock_ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
