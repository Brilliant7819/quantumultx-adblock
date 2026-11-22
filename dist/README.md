# 自建 QuantumultX 广告清单（多源聚合）

> 由 GitHub Actions 每日自动生成，无需手动维护。

## 上游源（广告）
anti-ad-quanx:102731 · anti-ad-surge:102731 · nobyda-adrule:7954 · hwind-splash-killer:415 · hwind-antihijack:186 · hwind-privacy:39895 · hwind-blockhttpdns:21 · easylistchina:6009 · easylist-intl:47993 · easyprivacy:47692 · adguard-base:2081 · adguard-mobile:970 · adguard-annoyance:1057 · adguard-social:60779 · adguard-tracking:120785 · adguard-gaming:191381 · adguard-chinese:6268 · adguard-annoyance2:625 · adguard-tracking-servers:732 · stevenblack:76088 · 1hosts:202830 · peterlowe:3554 · auto-ruddernation-designs-adobe-url-block-list-hosts:900 · auto-ethanaicode-adobe-block-hosts-list-hosts:902 · auto-emiliodallatorre-adult-hosts-list-hosts:13178 · auto-qianbinbin-killads-hosts:110345 · auto-bigdargon-hostsvn-hosts:18602 · auto-biroloter-mobile-ad-hosts-hosts:751 · auto-lonecoding-quantumultx-rules-china:3892 · auto-lonecoding-quantumultx-rules-apple:1814

## 上游源（解锁模块）
- sooyaaabo/Egern: 45 个模块
- BOBOLAOSHIV587/Rules: 20 个模块
> 每日验证可达性，死链自动剔除。

## 文件
- `splash-killer.list` —— 分流层（按域名 REJECT，无需 MITM）
- `adblock-splash.conf` —— 开屏广告重写（QX 原生，引用时 opt-parser=false）
- `adblock-feed.conf` —— 信息流/弹窗重写（QX 原生，引用时 opt-parser=false）
- `adblock-script.conf` —— 脚本层去广告（引用本仓库脚本，opt-parser=false）
- `splash-killer.js` / `feed-killer.js` —— 脚本本体
- `unlock-merged.conf` —— **全部解锁模块合并（QX 原生，opt-parser=false）**
- 仓库根目录 `quantumultx.conf` —— 合并了个人策略/DNS 的完整配置，不由本脚本覆盖

## QX 配置
整份可用配置：`https://raw.githubusercontent.com/Brilliant7819/quantumultx-adblock/main/quantumultx.conf`

远程资源不要开解析器（文件已是 QX 语法）。分流用分片，不要用整份 30 万行：

```ini
[filter_remote]
# 见 dist/qx-filter-remote.txt

[rewrite_remote]
https://raw.githubusercontent.com/Brilliant7819/quantumultx-adblock/main/dist/adblock-splash.conf, tag=自建-开屏重写, update-interval=28800, opt-parser=false, enabled=true
https://raw.githubusercontent.com/Brilliant7819/quantumultx-adblock/main/dist/adblock-feed.conf, tag=自建-信息流重写, update-interval=28800, opt-parser=false, enabled=true
https://raw.githubusercontent.com/Brilliant7819/quantumultx-adblock/main/dist/adblock-script.conf, tag=自建-脚本去广告, update-interval=28800, opt-parser=false, enabled=true
https://raw.githubusercontent.com/Brilliant7819/quantumultx-adblock/main/dist/unlock-merged.conf, tag=自建-解锁模块, update-interval=86400, opt-parser=false, enabled=true
```

> 分流是 QX 原生 `host-suffix`，必须 `opt-parser=false`，并且用 `qx/` 分片。整份 12MB 开解析器会超时，不开解析器也可能装不下。
> 上面 4 条重写同样 `opt-parser=false`。hostname 已经写在文件里，QX 会合并，不用解析器。

## 解锁模块
122 个模块合并（BOBOLAOSHIV QX 原生 + sooyaaabo Surge 转 QX + yqc007 裸脚本），1600 + 184 + 78 条规则，hostname 1006 个。

## 原作者致谢
本仓库聚合了以下上游开源项目的成果，**向每一位原作者致谢**（完整清单见 `CREDITS.md`）：
- 广告域名：anti-AD / hwind2021 / NobyDa / AdGuard 全系 / EasyList 中英 / EasyPrivacy / StevenBlack / 1Hosts / PeterLowe
- 解锁模块：BOBOLAOSHIV587 / app2smile / NobyDa / sooyaaabo(Egern) / yqc007
- 自动检索新增源见 `DISCOVERED.md`（由 discover_sources.py 每日 GitHub 搜索验证后收录）

## 统计
- 聚合广告域名: 304234 个
- 开屏重写 hostname: 437 个
- 信息流重写 hostname: 439 个
- 有效解锁模块: 122 个（合并 1600+184+78 条规则）

最后生成: 2026-11-22 14:13:19 UTC
