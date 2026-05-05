# Tauri 内嵌集成说明

VonishOCR 文档站支持双通道部署：在线版（GitHub Pages）与本地离线版（Tauri 内嵌）。本文档说明如何将 VitePress 构建产物集成到 Tauri 桌面应用中。

## 构建脚本配置

在 VonishOCR 主项目的 `package.json` 中添加文档构建脚本：

```json
{
  "scripts": {
    "docs:build": "cd docs && vitepress build",
    "docs:dev": "cd docs && vitepress dev"
  }
}
```

## 构建流程

### 1. 构建 VitePress 文档

```bash
cd docs
pnpm install
pnpm run build
```

构建产物输出至 `docs/.vitepress/dist/`。

### 2. 复制到 Tauri 公共资源目录

```bash
# 清理旧文档
rm -rf src-tauri/public/docs

# 复制构建产物
mkdir -p src-tauri/public/docs
cp -r docs/.vitepress/dist/* src-tauri/public/docs/

# 写入版本锁定文件
echo '{"version": "1.0.0", "build_time": "'$(date -Iseconds)'"}' > src-tauri/public/docs/version.json
```

### 3. Tauri 配置确认

`src-tauri/tauri.conf.json` 中确保 `resources` 或 `allowlist` 包含对 `public/docs` 的访问：

```json
{
  "bundle": {
    "resources": [
      "public/docs/**/*"
    ]
  }
}
```

## 应用内访问

### 方式一：直接打开本地 HTML

在 Tauri Rust 代码中，使用 `open()` 或 `WebView` 加载本地文档：

```rust
// 打开离线文档首页
let docs_path = app.path_resolver()
    .resolve_resource("public/docs/index.html")
    .expect("docs not found");

// 在系统浏览器中打开
open::that(docs_path)?;
```

### 方式二：内嵌 WebView（推荐）

在应用内新建窗口或 WebView 加载文档：

```rust
// 在主窗口中加载文档（通过自定义协议）
let docs_url = "tauri://localhost/docs/index.html";
window.eval(&format!("window.location.href = '{}'", docs_url))?;
```

或使用 Tauri 的自定义协议：

```rust
// 注册 asset 协议（Tauri v2）
#[tauri::command]
fn get_docs_url() -> String {
    "asset://docs/index.html".to_string()
}
```

### 方式三：菜单入口

在主界面顶部状态条添加「帮助 → 离线文档」按钮：

```vue
<!-- TopBar.vue -->
<template>
  <div class="topbar">
    <!-- ... -->
    <div class="help-menu">
      <button @click="openDocs">帮助</button>
      <div class="dropdown">
        <a @click="openDocs">离线文档</a>
        <a @click="openOnlineDocs">在线文档</a>
        <a @click="openAbout">关于</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { open } from '@tauri-apps/plugin-shell'

function openDocs() {
  // 打开本地离线文档
  open('asset://docs/index.html')
}

function openOnlineDocs() {
  open('https://docs.vonishocr.com')
}
</script>
```

## 版本锁定机制

离线文档必须与软件版本严格锁定：

- 构建脚本在 `src-tauri/public/docs/version.json` 中写入当前软件版本
- 应用启动时读取 `version.json`，与当前软件版本对比
- 若版本不一致，提示用户「文档版本不匹配，建议更新」

`version.json` 格式：

```json
{
  "version": "1.0.0",
  "build_time": "2026-05-05T14:36:12+08:00",
  "git_commit": "6f45476"
}
```

## 构建自动化

推荐将文档复制步骤加入 Tauri 的 `beforeBuildCommand`：

```json
// tauri.conf.json
{
  "build": {
    "beforeBuildCommand": "pnpm run docs:build && node scripts/copy-docs.js",
    "beforeDevCommand": "pnpm run docs:dev"
  }
}
```

`scripts/copy-docs.js`：

```javascript
const fs = require('fs')
const path = require('path')

const src = path.join(__dirname, '../docs/.vitepress/dist')
const dest = path.join(__dirname, '../src-tauri/public/docs')

// 清理并复制
fs.rmSync(dest, { recursive: true, force: true })
fs.cpSync(src, dest, { recursive: true })

// 写入版本文件
const version = require('../package.json').version
fs.writeFileSync(
  path.join(dest, 'version.json'),
  JSON.stringify({ version, build_time: new Date().toISOString() }, null, 2)
)

console.log(`Docs copied: v${version}`)
```

## 注意事项

1. **路径引用**：离线文档中的所有资源路径必须为相对路径（VitePress 构建默认如此），避免绝对路径导致资源加载失败
2. **搜索功能**：VitePress 的本地搜索在离线环境中完全可用，无需网络
3. **外部链接**：文档中的 GitHub 链接等外部链接在离线时无法访问，但不会影响文档站本身的浏览
4. **字体加载**：Google Fonts 在离线时可能无法加载，建议将字体文件内嵌至 `public/fonts/` 并在 CSS 中引用本地路径

---

> 离线文档是 VonishOCR「主权」理念的延伸——即使在没有网络的环境中，用户也应该能够查阅完整的产品文档，不受任何外部服务的制约。
