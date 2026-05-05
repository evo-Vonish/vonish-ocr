# 贡献指南

VonishOCR 是开源项目，欢迎通过 Issue 与 Pull Request 参与贡献。

## PR 规范

### 标题格式

```
<type>(<scope>): <subject>
```

示例：

```
feat(scene): add table classification support
fix(preprocess): correct deskew angle calculation for inverted images
docs(api): clarify batch endpoint response format
refactor(ui): extract reusable Modal component from ConfigDrawer
```

### 描述模板

PR 描述应包含以下部分：

```markdown
## 变更内容
- 做了什么
- 为什么做

## 影响范围
- 哪些模块受影响
- 是否需要迁移指南

## 测试
- [ ] 单元测试通过
- [ ] 手动测试通过
- [ ] 视觉回归测试（如修改 UI）

## 截图
（如修改 UI，附前后对比截图）
```

## Commit 格式

遵循 [Conventional Commits](https://conventionalcommits.org/) 规范：

| Type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响功能） |
| `refactor` | 重构（既不修复 bug 也不添加功能） |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建流程、辅助工具 |

示例：

```
feat(ocr): add support for vertical text recognition
fix(batch): prevent queue deadlock when all workers fail
docs(readme): update system requirements for macOS
```

## 代码风格

### 前端（Vue / JavaScript）

- ESLint 配置继承 `@vue/eslint-config-standard`
- Prettier 配置：
  - `semi: false`
  - `singleQuote: true`
  - `tabWidth: 2`
  - `trailingComma: 'es5'`
- Vue 组件使用组合式 API（`<script setup>`）
- 组件名大驼峰，组合式函数以 `use` 开头

### 后端（Python）

- 使用 Black 格式化：`black backend/`
- 行宽 100 字符
- 类型注解：所有函数参数与返回值必须标注类型
- 文档字符串：所有公共函数必须有 Google Style 文档字符串

```python
def recognize(image: Image.Image, scene: str = "auto") -> OCRResult:
    """执行 OCR 识别。
    
    Args:
        image: 输入图像，RGB 模式。
        scene: 场景分类标签，"auto" 表示自动判断。
    
    Returns:
        OCRResult 对象，包含 text、confidence、boxes。
    
    Raises:
        ModelNotLoadedError: 模型未加载时抛出。
    """
```

### Rust

- 使用 `rustfmt` 格式化
- 遵循 `cargo clippy` 的警告建议
- 错误处理优先使用 `Result` 与 `?` 操作符，避免 `.unwrap()`

## Issue 模板

### Bug 报告

```markdown
**描述**
简洁描述 bug 现象。

**复现步骤**
1. 打开软件
2. 执行某操作
3. 观察到某现象

**期望行为**
应该发生什么。

**实际行为**
实际发生了什么。

**环境**
- 操作系统：
- VonishOCR 版本：
- 模型档位：

**日志**
粘贴相关日志片段（`logs/backend.log`）。
```

### 功能请求

```markdown
**需求描述**
简洁描述想要的功能。

**使用场景**
这个功能在什么场景下有用。

**可能的实现方案**
（可选）你认为可以如何实现。

**替代方案**
（可选）当前是否有 workaround。
```

### 文档修正

```markdown
**位置**
文档文件路径与段落。

**当前内容**
当前写了什么。

**建议修改**
应该改成什么。

**理由**
为什么需要修改。
```

---

> 贡献规范的目的是降低协作成本。当每一位贡献者都遵循相同的格式与流程时，Code Review 可以聚焦于代码本身，而非格式与风格争论。
