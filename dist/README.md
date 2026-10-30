# 自建 QuantumultX 广告清单（多源聚合）

> 由 GitHub Actions 每日自动生成，无需手动维护。

## 上游源
anti-ad-quanx:100686 · anti-ad-surge:100686 · nobyda-adrule:7955 · hwind-splash-killer:412 · hwind-antihijack:186 · hwind-privacy:39898 · hwind-blockhttpdns:21

## 文件
- `splash-killer.list` —— 分流层（按域名 REJECT，无需 MITM）
- `adblock-splash.conf` —— 开屏广告重写（含 hostname，opt-parser=true 自动合并）
- `adblock-feed.conf` —— 信息流/弹窗重写（含 hostname）
- `adblock-script.conf` —— 脚本层去广告（引用本仓库脚本）
- `splash-killer.js` / `feed-killer.js` —— 脚本本体

## QX 配置
```ini
[filter_remote]
https://raw.githubusercontent.com/OWNER/REPO/main/dist/splash-killer.list, tag=自建-开屏分流, update-interval=28800, opt-parser=true, enabled=true

[rewrite_remote]
https://raw.githubusercontent.com/OWNER/REPO/main/dist/adblock-splash.conf, tag=自建-开屏重写, update-interval=28800, opt-parser=true, enabled=true
https://raw.githubusercontent.com/OWNER/REPO/main/dist/adblock-feed.conf, tag=自建-信息流重写, update-interval=28800, opt-parser=true, enabled=true
https://raw.githubusercontent.com/OWNER/REPO/main/dist/adblock-script.conf, tag=自建-脚本去广告, update-interval=28800, opt-parser=true, enabled=true
```

## 统计
- 聚合广告域名: 109387 个
- 开屏重写 hostname: 434 个
- 信息流重写 hostname: 436 个

最后生成: 2026-10-30 08:21:48 UTC
