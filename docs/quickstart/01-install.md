# 安装与启动

VonishOCR 支持 Windows、macOS、Linux 与 Android 四个平台。以下分别说明各平台的安装步骤与注意事项。

## Windows

### 安装步骤

1. 访问 [GitHub Releases](https://github.com/evo-Vonish/vonish-ocr/releases) 下载最新版本的 `.msi` 或 `.exe` 安装包
2. 双击安装包，按向导完成安装（默认路径：`C:\Program Files\VonishOCR`）
3. 首次启动时，软件会自动检查并预加载默认模型（标准档，约 80MB）
4. 预加载完成后，主界面出现「中央拖拽区」，表示安装成功

### 系统要求

| 项目 | 最低配置 | 推荐配置 |
|------|---------|---------|
| 操作系统 | Windows 10 1903+ | Windows 11 |
| 内存 | 4 GB | 8 GB |
| 显存 | 集成显卡可用 | 8 GB 独立显存（GPU 加速）|
| 磁盘空间 | 2 GB | 10 GB（含三档模型）|

### 注意事项

- 安装路径避免包含中文或空格，以防 Python sidecar 路径解析异常
- 首次启动的模型预加载可能需要 1-3 分钟，取决于网络与磁盘速度
- 若安全软件拦截，请将 VonishOCR 加入白名单（本地模型加载涉及 ONNXRuntime 的动态库调用）

## macOS

### 安装步骤

1. 下载 `.dmg` 文件并打开
2. 将 VonishOCR 拖拽至 Applications 文件夹
3. 首次启动时，系统可能提示「无法验证开发者」，前往「系统设置 → 隐私与安全性」点击「仍要打开」
4. 同意文件访问权限请求（模型与日志需要写入应用支持目录）

### 系统要求

- macOS 12 (Monterey) 或更高版本
- Apple Silicon 与 Intel 均支持，Apple Silicon 设备推理速度更快

## Linux

### 安装方式一：AppImage

1. 下载 `.AppImage` 文件
2. 赋予执行权限：`chmod +x VonishOCR-x86_64.AppImage`
3. 直接运行：`./VonishOCR-x86_64.AppImage`

### 安装方式二：deb 包

```bash
sudo dpkg -i vonishocr_1.0.0_amd64.deb
sudo apt-get install -f  # 自动解决依赖
```

### 依赖说明

Linux 版本依赖以下系统库，通常现代发行版已预装：

- `libgomp1`（OpenMP 运行时）
- `libgl1-mesa-glx`（OpenGL 支持）
- `onnxruntime` 动态库（已内嵌于安装包）

## Android

1. 下载 `.apk` 文件
2. 允许「安装未知来源应用」权限
3. 安装完成后，授予存储权限以便读取本地图片

Android 版本目前提供标准模型档位，专业模型因体积限制（1.87GB）暂未支持。批量处理能力根据设备内存自动调整并发数。

## 首次启动后的检查清单

- [ ] 主界面出现中央拖拽区（空状态）
- [ ] 左侧工具抽屉显示当前模型为「标准档」
- [ ] 顶部状态条显示「后端就绪」绿色指示灯
- [ ] 点击「后端控制台」按钮，算力仪表盘正常显示硬件信息
- [ ] 拖入一张测试图片，3 秒内出现识别结果

若以上任一项异常，请参阅[诊断与排错](/operations/02-troubleshooting)。

---

> 安装完成后，建议先阅读[首次识别](/quickstart/02-first-ocr)，在 3 分钟内完成第一张图片的识别全流程。
