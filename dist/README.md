# 自建 QuantumultX 广告清单（多源聚合）

> 由 GitHub Actions 每日自动生成，无需手动维护。

## 上游源（广告）
anti-ad-quanx:100682 · anti-ad-surge:100682 · nobyda-adrule:7955 · hwind-splash-killer:412 · hwind-antihijack:186 · hwind-privacy:39898 · hwind-blockhttpdns:21 · easylistchina:6094 · adguard-base:2080 · adguard-mobile:968 · adguard-annoyance:1049

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
65 个模块合并（BOBOLAOSHIV QX 原生 + sooyaaabo Surge 转 QX + yqc007 裸脚本），26 + 155 + 84 条规则，hostname 278 个。

## 统计
- 聚合广告域名: 113096 个
- 开屏重写 hostname: 434 个
- 信息流重写 hostname: 436 个
- 有效解锁模块: 65 个（合并 26+155+84 条规则）

最后生成: 2026-10-31 08:18:23 UTC
