# 开源生态

VonishOCR 建立在丰富的开源生态之上，以下向所有核心依赖的开发者致谢。

## 核心依赖

| 项目 | 用途 | 许可证 |
|------|------|--------|
| [Tauri](https://tauri.app/) | 桌面应用框架（Rust） | MIT / Apache-2.0 |
| [Vue.js](https://vuejs.org/) | 前端组件框架 | MIT |
| [Tailwind CSS](https://tailwindcss.com/) | 原子化 CSS | MIT |
| [FastAPI](https://fastapi.tiangolo.com/) | Python Web 框架 | MIT |
| [ONNXRuntime](https://onnxruntime.ai/) | 跨平台推理引擎 | MIT |
| [RapidOCR](https://github.com/RapidAI/RapidOCR) | 轻量级 OCR 模型 | Apache-2.0 |
| [CnOCR](https://github.com/breezedeus/cnocr) | 中文 OCR 模型 | MIT |
| [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | 版面分析与公式检测 | Apache-2.0 |
| [OpenCV](https://opencv.org/) | 图像预处理 | Apache-2.0 |
| [Uvicorn](https://www.uvicorn.org/) | ASGI 服务器 | BSD-3-Clause |
| [Pinia](https://pinia.vuejs.org/) | Vue 状态管理 | MIT |

## 字体许可

| 字体 | 用途 | 许可证 |
|------|------|--------|
| Noto Sans SC | 正文、UI 文字 | SIL Open Font License |
| Noto Serif SC | 标题、碑刻感展示 | SIL Open Font License |
| JetBrains Mono | 代码、数据读数 | SIL Open Font License |

字体文件内嵌于应用安装包中，用户无需联网下载。字体许可证允许嵌入、修改与再分发，但要求保留版权声明。

## 开源合规

VonishOCR 的许可证为 MIT，允许：

- 自由使用（个人、商业、教育）
- 自由修改
- 自由分发
- 自由再许可

唯一要求：在分发时保留原始版权声明与许可证文本。

各依赖项目的许可证文件位于：

```
src-tauri/Cargo.toml          # Rust 依赖许可证声明
backend/requirements.txt      # Python 依赖列表
package.json                  # Node.js 依赖列表
```

## 致谢

感谢以下开源项目与社区为 VonishOCR 提供的基础设施：

- **RapidAI 团队**：rapidocr 的快速推理与轻量模型
- **breezedeus**：cnocr 的中文识别精度与持续迭代
- **PaddlePaddle 团队**：PaddleOCR 的版面分析能力
- **Tauri 社区**：安全的桌面应用打包方案
- **Vue.js 团队**：渐进式前端框架的优雅设计

---

> 开源不是「免费使用」，而是「共同拥有」。VonishOCR 的每一个功能都站在开源社区的肩膀上，因此我们也以 MIT 许可证回馈社区——让这盏灯照亮更多人。
