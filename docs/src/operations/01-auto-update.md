# 自动更新

VonishOCR 的自动更新系统通过 GitHub Releases 与 Tauri Updater 插件实现，确保用户始终使用最新版本。

## 版本检查机制

启动时，VonishOCR 会异步查询 GitHub Releases API：

```
GET https://api.github.com/repos/evo-Vonish/vonish-ocr/releases/latest
```

查询结果与本地版本号对比。若远端版本更新，顶部状态条出现「更新可用」提示，点击后打开更新弹窗。

版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)：

```
主版本号.次版本号.修订号
```

示例：`1.0.0`、`1.1.0`、`1.1.1`。主版本号变更表示不兼容的 API 修改，次版本号变更表示功能新增，修订号变更表示 bug 修复。

## Tauri Updater 配置

`src-tauri/Cargo.toml` 中的 updater 配置：

```toml
[tauri.bundle]
identifier = "com.vonishocr.app"

[tauri.updater]
active = true
endpoints = [
  "https://github.com/evo-Vonish/vonish-ocr/releases/latest/download/latest.json"
]
pubkey = "YOUR_UPDATER_SIGNATURE_PUBKEY"
```

`latest.json` 格式：

```json
{
  "version": "1.1.0",
  "notes": "新增 AI Refiner 多厂商支持，优化批量处理性能",
  "pub_date": "2026-05-05T10:00:00Z",
  "platforms": {
    "windows-x86_64": {
      "signature": "...",
      "url": "https://github.com/evo-Vonish/vonish-ocr/releases/download/v1.1.0/VonishOCR_1.1.0_x64_en-US.msi.zip"
    },
    "darwin-x86_64": {
      "signature": "...",
      "url": "https://github.com/evo-Vonish/vonish-ocr/releases/download/v1.1.0/VonishOCR_1.1.0_x64.dmg"
    },
    "linux-x86_64": {
      "signature": "...",
      "url": "https://github.com/evo-Vonish/vonish-ocr/releases/download/v1.1.0/vonish-ocr_1.1.0_amd64.AppImage.tar.gz"
    }
  }
}
```

## 更新包签名与验证

Tauri updater 要求更新包必须经私钥签名，公钥内置于应用中。签名流程：

1. 构建完成后，生成更新包的 SHA256 摘要
2. 使用私钥对摘要进行 Ed25519 签名
3. 将签名写入 `latest.json` 的 `signature` 字段
4. 客户端下载后，用内置公钥验证签名，不通过则拒绝安装

## 用户侧更新流程

```
检测新版本
  → 弹窗提示「VonishOCR 1.1.0 可用」
  → 展示更新日志（Release Notes）
  → 用户点击「下载并安装」
  → 后台下载更新包（进度条显示）
  → 签名验证通过
  → 提示「重启以完成更新」
  → 用户确认重启
  → 应用关闭，更新程序接管
  → 安装完成，自动启动新版本
```

更新下载支持断点续传。若下载中断，下次启动时从断点继续，无需重新下载完整包。

## 离线版文档的版本锁定

离线文档（Tauri 内嵌的 VitePress 构建产物）与软件版本严格锁定：

- v1.0 软件携带 v1.0 文档
- v1.1 软件携带 v1.1 文档（含新增功能的说明）
- 文档版本号写入 `docs/.vitepress/dist/version.json`

用户可在「关于」弹窗中查看当前软件的文档版本，确保离线查阅的内容与软件功能一致。

---

> 自动更新的设计原则是「不打扰」。版本检查在后台异步完成，下载在后台静默进行，只有在需要用户决策（确认安装、确认重启）时才弹出界面。用户也可以选择「跳过此版本」，该决定会被记录，一周内不再提示同一版本。
