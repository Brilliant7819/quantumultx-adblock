# 自建 QuantumultX 广告清单（多源聚合）

> 由 GitHub Actions 每日自动生成，无需手动维护。

## 上游源（广告）
anti-ad-quanx:102731 · anti-ad-surge:102731 · nobyda-adrule:7954 · hwind-splash-killer:415 · hwind-antihijack:186 · hwind-privacy:39895 · hwind-blockhttpdns:21 · easylistchina:6309 · easylist-intl:47611 · easyprivacy:47678 · adguard-base:2081 · adguard-mobile:970 · adguard-annoyance:1057 · adguard-social:60396 · adguard-tracking:120775 · adguard-gaming:191281 · adguard-chinese:6569 · adguard-annoyance2:625 · adguard-tracking-servers:732 · stevenblack:76088 · 1hosts:202830 · peterlowe:3554 · auto-ruddernation-designs-adobe-url-block-list-hosts:900 · auto-ethanaicode-adobe-block-hosts-list-hosts:902 · auto-emiliodallatorre-adult-hosts-list-hosts:13178 · auto-qianbinbin-killads-hosts:110345 · auto-bigdargon-hostsvn-hosts:18602 · auto-biroloter-mobile-ad-hosts-hosts:751 · auto-lonecoding-quantumultx-rules-china:3892 · auto-lonecoding-quantumultx-rules-apple:1814

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
https://raw.githubusercontent.com/Brilliant7819/quantumultx-adblock/main/dist/splash-killer.list, tag=自建-开屏分流, update-interval=28800, opt-parser=false, enabled=true

[rewrite_remote]
https://raw.githubusercontent.com/Brilliant7819/quantumultx-adblock/main/dist/adblock-splash.conf, tag=自建-开屏重写, update-interval=28800, opt-parser=true, enabled=true
https://raw.githubusercontent.com/Brilliant7819/quantumultx-adblock/main/dist/adblock-feed.conf, tag=自建-信息流重写, update-interval=28800, opt-parser=true, enabled=true
https://raw.githubusercontent.com/Brilliant7819/quantumultx-adblock/main/dist/adblock-script.conf, tag=自建-脚本去广告, update-interval=28800, opt-parser=true, enabled=true
https://raw.githubusercontent.com/Brilliant7819/quantumultx-adblock/main/dist/unlock-merged.conf, tag=自建-解锁模块, update-interval=86400, opt-parser=true, enabled=true
```

> 分流是 QX 原生 `host-suffix`，必须 `opt-parser=false`。开了解析器会在手机上转 30 万行然后超时，整条引用报错。
> 重写保持 `opt-parser=true`，用来合并 hostname。
> 整份分流如果手机装不下，改用 `qx-filter-remote.txt` 里的分片（同样 opt-parser=false）。

## 解锁模块
122 个模块合并（BOBOLAOSHIV QX 原生 + sooyaaabo Surge 转 QX + yqc007 裸脚本），1600 + 184 + 78 条规则，hostname 1006 个。

## 原作者致谢
本仓库聚合了以下上游开源项目的成果，**向每一位原作者致谢**（完整清单见 `CREDITS.md`）：
- 广告域名：anti-AD / hwind2021 / NobyDa / AdGuard 全系 / EasyList 中英 / EasyPrivacy / StevenBlack / 1Hosts / PeterLowe
- 解锁模块：BOBOLAOSHIV587 / app2smile / NobyDa / sooyaaabo(Egern) / yqc007
- 自动检索新增源见 `DISCOVERED.md`（由 discover_sources.py 每日 GitHub 搜索验证后收录）

## 统计
- 聚合广告域名: 303830 个
- 开屏重写 hostname: 437 个
- 信息流重写 hostname: 439 个
- 有效解锁模块: 122 个（合并 1600+184+78 条规则）

最后生成: 2026-11-21 12:47:47 UTC
