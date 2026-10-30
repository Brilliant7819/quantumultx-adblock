# 自建 QuantumultX 广告清单（多源聚合）

> 由 GitHub Actions 每日自动生成，无需手动维护。

## 上游源（广告）
anti-ad-quanx:100686 · anti-ad-surge:100686 · nobyda-adrule:7955 · hwind-splash-killer:412 · hwind-antihijack:186 · hwind-privacy:39898 · hwind-blockhttpdns:21 · easylistchina:6083 · adguard-base:2080 · adguard-mobile:968 · adguard-annoyance:1049

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
65 个有效模块（死链已剔除）。

## 统计
- 聚合广告域名: 113089 个
- 开屏重写 hostname: 434 个
- 信息流重写 hostname: 436 个
- 有效解锁模块: 65 个

<<<<<<< HEAD
最后生成: 2026-10-30 08:22:39 UTC
=======
最后生成: 2026-10-30 08:36:29 UTC
>>>>>>> b6c775d (feat: v3 多源聚合+国际源(easylistchina/adguard) + 65个解锁模块同步)
