# 自建 QuantumultX 广告清单（多源聚合）

> 由 GitHub Actions 每日自动生成，无需手动维护。

## 上游源（广告）
anti-ad-quanx:101626 · anti-ad-surge:101626 · nobyda-adrule:7954 · hwind-splash-killer:413 · hwind-antihijack:186 · hwind-privacy:39895 · hwind-blockhttpdns:21 · easylistchina:6214 · easylist-intl:45582 · easyprivacy:47572 · adguard-base:2081 · adguard-mobile:969 · adguard-annoyance:1055 · adguard-social:58351 · adguard-tracking:119309 · adguard-gaming:187708 · adguard-chinese:6469 · adguard-annoyance2:626 · adguard-tracking-servers:730 · stevenblack:78201 · 1hosts:202830 · peterlowe:3560

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
82 个模块合并（BOBOLAOSHIV QX 原生 + sooyaaabo Surge 转 QX + yqc007 裸脚本），63 + 155 + 84 条规则，hostname 312 个。

## 统计
- 聚合广告域名: 289493 个
- 开屏重写 hostname: 435 个
- 信息流重写 hostname: 437 个
- 有效解锁模块: 82 个（合并 63+155+84 条规则）

最后生成: 2026-11-11 00:31:44 UTC
