const backZh = { text: '← 返回卷宗室', link: '/' }
const backEn = { text: '← Back to Archive', link: '/en/' }

const sidebarZh = {}
const sidebarEn = {}

/* ===== 简体中文 ===== */

sidebarZh['/'] = [
  {
    text: 'VonishOCR',
    collapsed: false,
    items: [
      { text: '首页', link: '/' },
      { text: '快速开始', link: '/quickstart/01-install' }
    ]
  },
  {
    text: '产品',
    collapsed: false,
    items: [
      { text: '产品介绍', link: '/product/01-introduction' },
      { text: '产品形态', link: '/product/02-morphology' },
      { text: '场景指南', link: '/product/03-scenarios' },
      { text: '竞品对比', link: '/product/04-comparison' }
    ]
  },
  {
    text: '功能手册',
    items: [
      { text: '场景自适应', link: '/features/01-scene-adaptive' },
      { text: '三档模型', link: '/features/02-models' },
      { text: 'Diff 复核', link: '/features/03-diff-review' },
      { text: '预处理引擎', link: '/features/04-preprocessing' },
      { text: 'AI 精修', link: '/features/05-ai-refiner' },
      { text: '批量流水线', link: '/features/06-batch-pipeline' },
      { text: '性能模式', link: '/features/07-performance' },
      { text: '后端控制台', link: '/features/08-backend-console' },
      { text: '导出与保存', link: '/features/09-export' }
    ]
  },
  {
    text: '设计系统',
    items: [
      { text: '品牌精神', link: '/design/01-brand' },
      { text: '三色成规', link: '/design/02-colors' },
      { text: '字体与排版', link: '/design/03-typography' },
      { text: '布局架构', link: '/design/04-layout' },
      { text: '组件规范', link: '/design/05-components' },
      { text: '主题系统', link: '/design/06-themes' },
      { text: '海报与视觉', link: '/design/07-visual' }
    ]
  },
  {
    text: '开发文档',
    items: [
      { text: '技术架构', link: '/development/01-architecture' },
      { text: '目录结构', link: '/development/02-structure' },
      { text: '本地开发环境', link: '/development/03-dev-env' },
      { text: '模型管理', link: '/development/04-model-mgmt' },
      { text: 'OCR 引擎', link: '/development/05-ocr-engine' },
      { text: 'AI Refiner', link: '/development/06-ai-refiner-dev' },
      { text: '前端重构', link: '/development/07-frontend-refactor' },
      { text: '后端控制台开发', link: '/development/08-backend-console-dev' },
      { text: '贡献指南', link: '/development/09-contributing' }
    ]
  },
  {
    text: '运维与生态',
    items: [
      { text: '自动更新', link: '/operations/01-auto-update' },
      { text: '诊断与排错', link: '/operations/02-troubleshooting' },
      { text: '模型缓存清理', link: '/operations/03-cache-cleanup' },
      { text: '日志审计', link: '/operations/04-log-audit' },
      { text: '开源生态', link: '/ecosystem/01-open-source' },
      { text: '社区', link: '/ecosystem/02-community' },
      { text: '路线图', link: '/ecosystem/03-roadmap' }
    ]
  }
]

;['product','quickstart','features','design','development','operations','ecosystem'].forEach(k => {
  sidebarZh[`/${k}/`] = [backZh, ...sidebarZh['/'].filter(g => {
    const first = g.items?.[0]?.link || ''
    return first.startsWith(`/${k}/`)
  })]
})

/* ===== English ===== */

sidebarEn['/en/'] = [
  {
    text: 'VonishOCR',
    collapsed: false,
    items: [
      { text: 'Home', link: '/en/' },
      { text: 'Quick Start', link: '/en/quickstart/install' }
    ]
  },
  {
    text: 'Product',
    collapsed: false,
    items: [
      { text: 'Introduction', link: '/en/product/introduction' },
      { text: 'Editions', link: '/en/product/editions' },
      { text: 'Scenarios', link: '/en/product/scenarios' },
      { text: 'Comparison', link: '/en/product/comparison' }
    ]
  },
  {
    text: 'Features',
    items: [
      { text: 'Adaptive Scenes', link: '/en/features/adaptive-scenes' },
      { text: 'Three-Tier Models', link: '/en/features/models' },
      { text: 'Diff Review', link: '/en/features/diff-review' },
      { text: 'Preprocessing', link: '/en/features/preprocessing' },
      { text: 'AI Refiner', link: '/en/features/ai-refiner' },
      { text: 'Batch Pipeline', link: '/en/features/batch' },
      { text: 'Performance', link: '/en/features/performance' },
      { text: 'Console', link: '/en/features/console' },
      { text: 'Export', link: '/en/features/export' }
    ]
  },
  {
    text: 'Design',
    items: [
      { text: 'Brand Spirit', link: '/en/design/brand' },
      { text: 'Three Colors', link: '/en/design/colors' },
      { text: 'Typography', link: '/en/design/typography' },
      { text: 'Layout', link: '/en/design/layout' },
      { text: 'Components', link: '/en/design/components' },
      { text: 'Themes', link: '/en/design/themes' },
      { text: 'Visual Identity', link: '/en/design/visual' }
    ]
  },
  {
    text: 'Development',
    items: [
      { text: 'Architecture', link: '/en/development/architecture' },
      { text: 'Structure', link: '/en/development/structure' },
      { text: 'Dev Environment', link: '/en/development/dev-env' },
      { text: 'Model Management', link: '/en/development/models' },
      { text: 'OCR Engine', link: '/en/development/ocr-engine' },
      { text: 'AI Refiner Dev', link: '/en/development/ai-refiner' },
      { text: 'Frontend Refactor', link: '/en/development/frontend' },
      { text: 'Backend Console', link: '/en/development/console' },
      { text: 'Contributing', link: '/en/development/contributing' }
    ]
  },
  {
    text: 'Operations & Ecosystem',
    items: [
      { text: 'Auto Update', link: '/en/operations/auto-update' },
      { text: 'Troubleshooting', link: '/en/operations/troubleshooting' },
      { text: 'Cache Cleanup', link: '/en/operations/cache-cleanup' },
      { text: 'Log Audit', link: '/en/operations/log-audit' },
      { text: 'Open Source', link: '/en/ecosystem/open-source' },
      { text: 'Community', link: '/en/ecosystem/community' },
      { text: 'Roadmap', link: '/en/ecosystem/roadmap' }
    ]
  }
]

;['product','quickstart','features','design','development','operations','ecosystem'].forEach(k => {
  sidebarEn[`/en/${k}/`] = [backEn, ...sidebarEn['/en/'].filter(g => {
    const first = g.items?.[0]?.link || ''
    return first.startsWith(`/en/${k}/`)
  })]
})

export default { ...sidebarZh, ...sidebarEn }
