# QuantumultX 广告清单自动生成器

> 你的个人 QuantumultX 广告去重仓库。**每天 04:17 UTC（北京时间 12:17）由 GitHub Actions 自动运行**，
> 聚合上游（anti-AD / NobyDa / hwind2021 / AdGuard 全系 / EasyList 中英 / EasyPrivacy / StevenBlack / 1Hosts / PeterLowe 等）广告资源
> \+ 76 个解锁/去广告模块（BOBOLAOSHIV / app2smile / NobyDa / sooyaaabo / yqc007），
> 生成可直接被 QX 拉取的远程清单。**你只需在 QX 里添加本仓库的 5 条远程引用，之后零维护。**

## 原理

```
GitHub Actions (cron 每日 04:17 UTC = 北京 12:17，避开整点高峰)
   └─ generator.py
        ├─ 拉取上游广告清单（anti-AD / NobyDa / hwind / AdGuard 全系 / EasyList 中英 / EasyPrivacy / StevenBlack / 1Hosts / PeterLowe）
        ├─ 聚合去重广告域名（约 28.5 万个，已剔子域名冗余）
        ├─ 拉取解锁模块（BOBOLAOSHIV + app2smile + NobyDa QX 原生 + sooyaaabo Surge 转 QX + yqc007 裸脚本）
        ├─ 合并为单个 unlock-merged.conf（285 条规则 + hostname）
        ├─ 自动生成 hostname 行（关键！解决 MITM hostname 问题）
        └─ 产出 dist/ 下的 8 个文件并自动提交
```

> **注意**：GitHub Actions 的 cron 是"尽量跑"，可能延迟或偶发跳过某天。若某天未跑，去仓库 Actions → `每日广告资源聚合` → `Run workflow` 手动触发即可。

## QX 配置（复制到你的 conf）

```ini
[filter_remote]
https://raw.githubusercontent.com/Brilliant7819/quantumultx-adblock/main/dist/splash-killer.list, tag=自建-开屏分流, update-interval=28800, opt-parser=true, enabled=true

[rewrite_remote]
https://raw.githubusercontent.com/Brilliant7819/quantumultx-adblock/main/dist/adblock-splash.conf, tag=自建-开屏重写, update-interval=28800, opt-parser=true, enabled=true
https://raw.githubusercontent.com/Brilliant7819/quantumultx-adblock/main/dist/adblock-feed.conf, tag=自建-信息流重写, update-interval=28800, opt-parser=true, enabled=true
https://raw.githubusercontent.com/Brilliant7819/quantumultx-adblock/main/dist/adblock-script.conf, tag=自建-脚本去广告, update-interval=28800, opt-parser=true, enabled=true
https://raw.githubusercontent.com/Brilliant7819/quantumultx-adblock/main/dist/unlock-merged.conf, tag=自建-解锁模块, update-interval=86400, opt-parser=true, enabled=true
```

> 全部 `opt-parser=true`：generator 已在每个 conf 末尾写入完整 `hostname` 行，
> QX 会自动合并进 MITM，无需手动维护 hostname。
> `unlock-merged.conf` 为**单个文件**，内含全部解锁规则 + hostname，QX 一键引用，无需手动复制多行。

## 生成产物

| 文件 | 作用 |
|---|---|
| `dist/splash-killer.list` | 分流层：按域名 REJECT（约 28.5 万个，已剔子域名冗余，无需 MITM） |
| `dist/adblock-splash.conf` | 重写：开屏广告（含 hostname） |
| `dist/adblock-feed.conf` | 重写：信息流/弹窗（含 hostname） |
| `dist/adblock-script.conf` | 脚本：引用本仓库 splash-killer.js |
| `dist/splash-killer.js` | 脚本：开屏杀手 |
| `dist/feed-killer.js` | 脚本：信息流杀手 |
| `dist/unlock-merged.conf` | **解锁模块单文件聚合**（285 规则 / hostname） |

## 广告源覆盖

- **anti-AD**：最强国内覆盖（约 10 万域名）
- **hwind2021**：开屏 SDK + 重写规则 + 脚本
- **NobyDa**：AdRule.list 补充
- **AdGuard 全系**：base / mobile / social / tracking / gaming / Chinese / annoyances / tracking-servers
- **EasyList 中国 + EasyList 国际 + EasyPrivacy**
- **StevenBlack / 1Hosts / PeterLowe**（hosts 格式，含国际广告/追踪）

## 解锁模块覆盖（76 个，285 条规则，单文件 `unlock-merged.conf`）

- **BOBOLAOSHIV**（20 个 QX 原生 `.conf`）
- **app2smile**（9 个 QX 模块：Spotify / Bilibili / 知乎 / 起点 / 腾讯新闻 / 贴吧 / VGtime / YouTube / AdSense 去广告）
- **NobyDa**（2 个 QX 模块：Js.conf 去微信广告/VIP/RevenueCat + TestFlightDownload.conf）
- **sooyaaabo/Egern**（45 个 Surge `.module` 转 QX）
- **yqc007/QuantumultX**（裸 `.js` 脚本，头部内嵌 QX 规则自动提取）

## 手动运行（本地）

```bash
python generator.py          # 重新生成 dist/
python generator.py --check-only   # 只检测上游可达性
```

## 说明

- 生成器只聚合**可在线访问**的上游（死链自动跳过，不会引入失效项）。
- 所有重写规则经 QX 原生 + KOP-XIAO parser 双重校验（剔除 `(?i)` 内联旗标、未知 action、非法 hostname、垃圾域名），确保 **0 issue**。
- 上游仓库变动会自动反映到你的清单，无需任何手动操作。
- 想改聚合范围：编辑 `generator.py` 里的 `FILTER_SOURCES` / `REWRITE_SOURCES` / `UNLOCK_*` 段。
