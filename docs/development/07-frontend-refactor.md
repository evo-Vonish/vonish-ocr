# 前端重构指南

VonishOCR 的前端重构围绕四区布局、设计 Token 与响应式断点展开。

## 四区布局 CSS Grid 实现

主界面的五区布局使用 CSS Grid 实现：

```vue
<!-- App.vue -->
<template>
  <div class="app-grid">
    <TopBar class="topbar" />
    <LeftRail class="left-rail" />
    <Workbench class="workbench" />
    <RightReview class="right-review" />
    <BottomBar class="bottom-bar" />
  </div>
</template>

<style scoped>
.app-grid {
  display: grid;
  grid-template-areas:
    "topbar    topbar      topbar"
    "left-rail workbench   right-review"
    "bottombar bottombar   bottombar";
  grid-template-columns: 280px 1fr 320px;
  grid-template-rows: 48px 1fr 40px;
  height: 100vh;
  background: var(--bg-carbon);
}

.topbar      { grid-area: topbar; }
.left-rail   { grid-area: left-rail; }
.workbench   { grid-area: workbench; }
.right-review { grid-area: right-review; }
.bottom-bar  { grid-area: bottombar; }

/* 平板：复核灯可收起 */
@media (max-width: 1279px) {
  .app-grid {
    grid-template-columns: 280px 1fr 48px;
  }
  .right-review {
    width: 48px;
    overflow: hidden;
  }
}

/* 窄屏：单栏堆叠 */
@media (max-width: 767px) {
  .app-grid {
    grid-template-areas:
      "topbar"
      "workbench"
      "bottombar";
    grid-template-columns: 1fr;
    grid-template-rows: 48px 1fr 40px;
  }
  .left-rail, .right-review {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 100;
  }
}
</style>
```

## 设计 Token CSS Variables

设计 Token 以 CSS 自定义属性的形式定义在 `:root`，供全应用使用：

```css
:root {
  /* 背景 */
  --bg-carbon: #11110F;
  --bg-dark: #1A1916;
  --bg-panel: #222026;
  
  /* 文字 */
  --text-paper: #E7E1D0;
  --text-steel: #A39B8F;
  --text-muted: #6B6560;
  
  /* 品牌 */
  --accent-lamp: #8FF6D2;
  --accent-lamp-72: rgba(143, 246, 210, 0.72);
  --accent-lamp-48: rgba(143, 246, 210, 0.48);
  --accent-lamp-32: rgba(143, 246, 210, 0.32);
  
  /* 边框 */
  --border-steel: #3D383F;
  
  /* 状态 */
  --status-warn: #D7B95A;
  --status-danger: #B85A50;
  
  /* 字体 */
  --font-serif: "Noto Serif SC", serif;
  --font-sans: "Noto Sans SC", sans-serif;
  --font-mono: "JetBrains Mono", monospace;
  
  /* 布局 */
  --rail-width: 280px;
  --review-width: 320px;
  --topbar-height: 48px;
  --bottombar-height: 40px;
  
  /* 动画 */
  --transition-fast: 150ms;
  --transition-medium: 180ms;
  --transition-slow: 300ms;
}
```

使用 Token 而非硬编码色值的好处：

1. 主题切换时只需覆写 Token，无需修改每个组件
2. 设计文档与代码实现保持同步
3. 新开发者无需记忆色值，通过语义化名称即可正确使用

## 响应式断点

| 名称 | 宽度 | 布局变化 |
|------|------|---------|
| `desktop` | ≥1280px | 五区全部常驻 |
| `tablet-lg` | 1024-1279px | 复核灯收缩为 48px 图标栏 |
| `tablet` | 768-1023px | 左抽屉收缩为图标栏，复核灯可覆盖 |
| `mobile` | <768px | 单栏堆叠，抽屉与复核灯变为底部 Drawer |

断点使用 CSS 媒体查询实现，JavaScript 中通过 `window.matchMedia` 检测：

```javascript
// composables/useBreakpoint.js
export function useBreakpoint() {
  const isDesktop = ref(window.innerWidth >= 1280)
  const isTablet = ref(window.innerWidth >= 768 && window.innerWidth < 1280)
  const isMobile = ref(window.innerWidth < 768)
  
  const update = () => {
    const w = window.innerWidth
    isDesktop.value = w >= 1280
    isTablet.value = w >= 768 && w < 1280
    isMobile.value = w < 768
  }
  
  window.addEventListener('resize', update)
  onUnmounted(() => window.removeEventListener('resize', update))
  
  return { isDesktop, isTablet, isMobile }
}
```

## 九个功能模块检查清单

前端重构时，需确保以下九个功能模块的完整性：

| # | 模块 | 关键组件 | 检查要点 |
|---|------|---------|---------|
| 1 | 上传与识别 | `UploadZone.vue` | 拖拽区、文件列表、批量队列 |
| 2 | 结果展示 | `ResultPanel.vue` | 原始/精修/Diff 三栏、低置信标记 |
| 3 | 场景分类 | 左抽屉场景区 | 自动标签、手动覆盖 |
| 4 | 模型切换 | 左抽屉模型区 | 三档选择、加载状态 |
| 5 | AI 精修 | `AIProviderCenter.vue` | 方案管理、流式输出 |
| 6 | 批量处理 | `UploadZone.vue` + 队列 | 进度条、状态标签、失败重试 |
| 7 | 配置系统 | `ConfigDrawer.vue` | 持久化、主题、性能模式 |
| 8 | 导出保存 | 底部读数区导出按钮 | 格式选择、批量打包 |
| 9 | 系统托盘 | Tauri 层 | 最小化到托盘、托盘菜单 |

---

> 前端重构不是重写，而是建立可维护的结构。CSS Grid 负责布局骨架，CSS Variables 负责设计系统，响应式断点负责跨设备适配——三层分离，互不侵入。
