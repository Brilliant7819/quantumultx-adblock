# QuantumultX 广告清单自动生成器

> 你的个人 QuantumultX 广告去重仓库。**每天 04:00 UTC（北京 12:00）由 GitHub Actions 自动运行**，
> 聚合上游（hwind2021/QuantumultX-AdBlock-CN 等）广告资源，生成可直接被 QX 拉取的远程清单。
> **你只需在 QX 里添加本仓库的 4 条远程引用，之后零维护。**

## 原理

```
GitHub Actions (cron 每日 04:00 UTC)
   └─ generator.py
        ├─ 拉取上游 Splash-Killer.list / AdBlock-*.conf / 脚本
        ├─ 聚合去重广告域名
        ├─ 自动生成 hostname 行（关键！解决"缺 hostname 不生效"）
        └─ 产出 dist/ 下的 6 个文件并自动提交
```

## QX 配置（复制到你的 conf）

```ini
[filter_remote]
https://raw.githubusercontent.com/OWNER/REPO/main/dist/splash-killer.list, tag=自建-开屏分流, update-interval=28800, opt-parser=true, enabled=true

[rewrite_remote]
https://raw.githubusercontent.com/OWNER/REPO/main/dist/adblock-splash.conf, tag=自建-开屏重写, update-interval=28800, opt-parser=true, enabled=true
https://raw.githubusercontent.com/OWNER/REPO/main/dist/adblock-feed.conf, tag=自建-信息流重写, update-interval=28800, opt-parser=true, enabled=true
https://raw.githubusercontent.com/OWNER/REPO/main/dist/adblock-script.conf, tag=自建-脚本去广告, update-interval=28800, opt-parser=true, enabled=true
```

> 全部 `opt-parser=true`：generator 已在每个 conf 末尾写入完整 `hostname` 行，
> QX 会自动合并进 MITM，无需手动维护 hostname。

## 生成产物

| 文件 | 层 | 作用 |
|---|---|---|
| `dist/splash-killer.list` | 分流 | 按域名 REJECT（无需 MITM） |
| `dist/adblock-splash.conf` | 重写 | 开屏广告（含 hostname） |
| `dist/adblock-feed.conf` | 重写 | 信息流/弹窗（含 hostname） |
| `dist/adblock-script.conf` | 脚本 | 引用本仓库 splash-killer.js |
| `dist/splash-killer.js` | 脚本 | 开屏杀手 |
| `dist/feed-killer.js` | 脚本 | 信息流杀手 |

## 手动运行（本地）

```bash
python generator.py          # 重新生成 dist/
python generator.py --check-only   # 只检测上游可达
```

## 说明

- 生成器只聚合**可在线访问**的上游（死链自动跳过，不会引入失效项）。
- 上游仓库变动会自动反映到你的清单，无需任何手动操作。
- 想改聚合范围：编辑 `generator.py` 里的 `SOURCES` / `SCRIPTS`。
