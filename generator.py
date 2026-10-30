#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantumultX 广告资源自动生成器
================================
每天定时拉取上游资源，聚合去重，生成：
  - dist/splash-killer.list     分流层（HOST-SUFFIX / HOST / HOST-KEYWORD / REJECT）
  - dist/adblock-splash.conf    开屏广告重写（含自动 hostname 行）
  - dist/adblock-feed.conf      信息流/弹窗广告重写（含自动 hostname 行）
  - dist/adblock-script.conf    脚本层去广告（引用本仓库 splash-killer.js）
  - dist/splash-killer.js       脚本本体（从上游复制，保证可用）
  - dist/feed-killer.js         脚本本体
  - dist/README.md              使用说明 + 时间戳

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

BASE = "https://raw.githubusercontent.com/hwind2021/QuantumultX-AdBlock-CN/main/quantumultx"

# 本仓库 raw 前缀（Actions 里会被替换成真实仓库地址）
REPO_RAW = "${REPO_RAW}"

SOURCES = {
    # 分流层：直接按域名拦截，无需 MITM
    "splash_killer": f"{BASE}/filter/Splash-Killer.list",
    # 重写层：需要 MITM，规则里可提取域名
    "adblock_splash": f"{BASE}/rewrite/AdBlock-Splash.conf",
    "adblock_feed": f"{BASE}/rewrite/AdBlock-Feed.conf",
    # 脚本层：引用 JS
    "adblock_script": f"{BASE}/rewrite/AdBlock-Script.conf",
}

SCRIPTS = {
    "splash-killer.js": f"{BASE}/script/splash-killer.js",
    "feed-killer.js": f"{BASE}/script/feed-killer.js",
}

OUT = Path(__file__).parent / "dist"


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "adblock-gen/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def norm(line):
    """归一化一条规则/域名行，去掉注释与空白。"""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    return line


def extract_hosts(text):
    """从一条重写规则里提取显式域名（处理 \. 转义）。"""
    hosts = set()
    for line in text.splitlines():
        line = norm(line)
        if not line:
            continue
        m = re.match(r"^(?:\^|\(\?i\))?https?\??:\/\/([^\/\s,]+)", line)
        if not m:
            continue
        h = m.group(1)
        h = h.replace("\\/", "/").replace("\\.", ".").replace("\\d", "d").replace("\\w", "w")
        if not re.search(r"[\[\]?*()\\{}|]", h):
            hosts.add(h.rstrip(".").lower())
    return hosts


def extract_splash_domains(text):
    """从 Splash-Killer.list（分流层）提取全部域名：HOST / HOST-SUFFIX / HOST-KEYWORD。
    这些是广告 SDK 域名，直接作为 MITM hostname，使路径型重写规则也能生效。"""
    hosts = set()
    for line in text.splitlines():
        line = norm(line)
        if not line:
            continue
        if re.match(r"^(HOST|HOST-SUFFIX),", line):
            parts = line.split(",")
            if len(parts) >= 2:
                d = parts[1].strip().lower().rstrip(".")
                if d and re.search(r"[a-z0-9-]+\.[a-z]{2,}", d):
                    hosts.add(d)
    return hosts


def gen_hostname(hosts):
    """生成 QX hostname 行（逗号分隔，最长 180 字符换行）。"""
    items = sorted(hosts)
    if not items:
        return ""
    lines, cur = [], ""
    for it in items:
        if len(cur) + len(it) + 1 > 180:
            lines.append(cur)
            cur = it
        else:
            cur = (cur + "," + it) if cur else it
    if cur:
        lines.append(cur)
    return "hostname = " + ",\n".join(lines)


def gen_splash_list(text):
    """分流层：透传 Splash-Killer.list 的非注释行，确保策略为 REJECT。"""
    out = ["# NAME: Splash-Killer (自建聚合)", "# POLICY: REJECT", "# 由 generator.py 自动生成", ""]
    seen = set()
    for line in text.splitlines():
        line = norm(line)
        if not line:
            continue
        # 只保留 HOST / HOST-SUFFIX / HOST-KEYWORD 行，统一 REJECT
        if re.match(r"^(HOST|HOST-SUFFIX|HOST-KEYWORD),", line):
            parts = line.split(",")
            if len(parts) >= 2:
                key = f"{parts[0]},{parts[1].strip().lower()}"
                if key not in seen:
                    seen.add(key)
                    out.append(f"{parts[0]},{parts[1].strip()},REJECT")
    return "\n".join(out)


def gen_rewrite(text, name, desc, hosts):
    """重写层：透传规则，末尾补 hostname。"""
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
    """脚本层：把上游脚本 URL 改成本仓库的 splash-killer.js / feed-killer.js。"""
    out = ["# NAME: AdBlock-Script (自建聚合)", "# DESC: JS 脚本去广告，引用本仓库脚本", "# 由 generator.py 自动生成", ""]
    for line in text.splitlines():
        line = norm(line)
        if not line:
            continue
        # 替换远程脚本 URL 为本仓库脚本（splash-killer.js / feed-killer.js）
        line = re.sub(
            r"https?:\/\/[^\s]+\.js",
            f"{repo_raw}/splash-killer.js",
            line,
        )
        out.append(line)
    return "\n".join(out)


def main():
    check_only = "--check-only" in sys.argv
    ok = True

    # 1) 拉取全部上游
    raw = {}
    for name, url in SOURCES.items():
        try:
            raw[name] = fetch(url)
            print(f"  [OK] {name}: {len(raw[name])} bytes")
        except Exception as e:
            ok = False
            print(f"  [FAIL] {name}: {e}")
            raw[name] = ""

    if check_only:
        print("CHECK:", "PASS" if ok else "FAIL")
        return 0 if ok else 1

    # 2) 聚合域名
    #    核心：从 Splash-Killer.list（468 广告域名）提取，这是路径型重写规则生效的前提
    splash_domains = extract_splash_domains(raw["splash_killer"])
    splash_hosts = extract_hosts(raw["adblock_splash"])
    feed_hosts = extract_hosts(raw["adblock_feed"])
    # 并集：分流层域名 + 重写层显式域名
    all_hosts = splash_domains | splash_hosts | feed_hosts
    # 每个 conf 的 hostname：自身显式域名 + 分流层全量域名（保证路径型规则可匹配）
    splash_conf_hosts = splash_hosts | splash_domains
    feed_conf_hosts = feed_hosts | splash_domains

    print(f"  域名统计: 分流层 {len(splash_domains)} · 开屏显式 {len(splash_hosts)} · 信息流显式 {len(feed_hosts)} · 聚合 {len(all_hosts)}")

    # 3) 生成分流
    splash_list = gen_splash_list(raw["splash_killer"])

    # 4) 生成重写（含 hostname）
    splash_conf = gen_rewrite(raw["adblock_splash"], "AdBlock-Splash",
                              "开屏广告重写（含自动 hostname）", splash_conf_hosts)
    feed_conf = gen_rewrite(raw["adblock_feed"], "AdBlock-Feed",
                            "信息流/弹窗重写（含自动 hostname）", feed_conf_hosts)

    # 5) 生成脚本 conf（引用本仓库脚本）
    repo_raw = REPO_RAW if not REPO_RAW.startswith("$") else "https://raw.githubusercontent.com/OWNER/REPO/main/script"
    script_conf = gen_script_conf(raw["adblock_script"], repo_raw)

    # 6) 写文件
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "splash-killer.list").write_text(splash_list, encoding="utf-8")
    (OUT / "adblock-splash.conf").write_text(splash_conf, encoding="utf-8")
    (OUT / "adblock-feed.conf").write_text(feed_conf, encoding="utf-8")
    (OUT / "adblock-script.conf").write_text(script_conf, encoding="utf-8")

    for fname, url in SCRIPTS.items():
        try:
            (OUT / fname).write_text(fetch(url), encoding="utf-8")
            print(f"  [OK] script {fname}")
        except Exception as e:
            print(f"  [FAIL] script {fname}: {e}")

    ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    readme = f"""# 自建 QuantumultX 广告清单

> 由 GitHub Actions 每日自动生成，无需手动维护。

## 文件
- `splash-killer.list` —— 分流层（按域名 REJECT，无需 MITM）
- `adblock-splash.conf` —— 开屏广告重写（含 hostname，opt-parser=true 自动合并）
- `adblock-feed.conf` —— 信息流/弹窗重写（含 hostname）
- `adblock-script.conf` —— 脚本层去广告（引用本仓库脚本）
- `splash-killer.js` / `feed-killer.js` —— 脚本本体

## QX 配置（[filter_remote] / [rewrite_remote]）
```ini
[filter_remote]
https://raw.githubusercontent.com/OWNER/REPO/main/dist/splash-killer.list, tag=自建-开屏分流, update-interval=28800, opt-parser=true, enabled=true

[rewrite_remote]
https://raw.githubusercontent.com/OWNER/REPO/main/dist/adblock-splash.conf, tag=自建-开屏重写, update-interval=28800, opt-parser=true, enabled=true
https://raw.githubusercontent.com/OWNER/REPO/main/dist/adblock-feed.conf, tag=自建-信息流重写, update-interval=28800, opt-parser=true, enabled=true
https://raw.githubusercontent.com/OWNER/REPO/main/dist/adblock-script.conf, tag=自建-脚本去广告, update-interval=28800, opt-parser=true, enabled=true
```

## 统计
- 分流层广告域名: {len(splash_domains)} 个
- 开屏重写显式域名: {len(splash_hosts)} 个
- 信息流重写显式域名: {len(feed_hosts)} 个
- 聚合去重域名(MITM): {len(all_hosts)} 个

最后生成: {ts}
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    print(f"\n完成！生成 {len(list(OUT.glob('*')))} 个文件到 dist/")
    print(f"  聚合域名 {len(all_hosts)} 个 (含分流层 {len(splash_domains)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
