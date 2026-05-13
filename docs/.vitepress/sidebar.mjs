/** 全局常驻索引 — 用前缀覆盖确保所有子页都显示完整栏目树 */
const zh = [
  { text: 'VonishOCR', collapsed: false, items: [{ text: '首页', link: '/' }, { text: '快速开始', link: '/quickstart/01-install' }] },
  { text: '产品', collapsed: false, items: [{ text: '产品介绍', link: '/product/01-introduction' }, { text: '产品形态', link: '/product/02-morphology' }, { text: '场景指南', link: '/product/03-scenarios' }, { text: '竞品对比', link: '/product/04-comparison' }] },
  { text: '功能手册', collapsed: false, items: [{ text: '场景自适应', link: '/features/01-scene-adaptive' }, { text: '三档模型', link: '/features/02-models' }, { text: 'Diff 复核', link: '/features/03-diff-review' }, { text: '预处理引擎', link: '/features/04-preprocessing' }, { text: 'AI 精修', link: '/features/05-ai-refiner' }, { text: '批量流水线', link: '/features/06-batch-pipeline' }, { text: '性能模式', link: '/features/07-performance' }, { text: '后端控制台', link: '/features/08-backend-console' }, { text: '导出与保存', link: '/features/09-export' }] },
  { text: '设计系统', collapsed: false, items: [{ text: '品牌精神', link: '/design/01-brand' }, { text: '三色成规', link: '/design/02-colors' }, { text: '字体与排版', link: '/design/03-typography' }, { text: '布局架构', link: '/design/04-layout' }, { text: '组件规范', link: '/design/05-components' }, { text: '主题系统', link: '/design/06-themes' }, { text: '海报与视觉', link: '/design/07-visual' }] },
  { text: '开发文档', collapsed: false, items: [{ text: '技术架构', link: '/development/01-architecture' }, { text: '目录结构', link: '/development/02-structure' }, { text: '本地开发环境', link: '/development/03-dev-env' }, { text: '模型管理', link: '/development/04-model-mgmt' }, { text: 'OCR 引擎', link: '/development/05-ocr-engine' }, { text: 'AI Refiner', link: '/development/06-ai-refiner-dev' }, { text: '前端重构', link: '/development/07-frontend-refactor' }, { text: '后端控制台开发', link: '/development/08-backend-console-dev' }, { text: '贡献指南', link: '/development/09-contributing' }] },
  { text: '运维与生态', collapsed: false, items: [{ text: '自动更新', link: '/operations/01-auto-update' }, { text: '诊断与排错', link: '/operations/02-troubleshooting' }, { text: '模型缓存清理', link: '/operations/03-cache-cleanup' }, { text: '日志审计', link: '/operations/04-log-audit' }, { text: '开源生态', link: '/ecosystem/01-open-source' }, { text: '社区', link: '/ecosystem/02-community' }, { text: '路线图', link: '/ecosystem/03-roadmap' }] },
]

const en = [
  { text: 'VonishOCR', collapsed: false, items: [{ text: 'Home', link: '/en/' }, { text: 'Quick Start', link: '/en/quickstart/01-install' }] },
  { text: 'Product', collapsed: false, items: [{ text: 'Introduction', link: '/en/product/01-introduction' }, { text: 'Editions', link: '/en/product/02-morphology' }, { text: 'Scenarios', link: '/en/product/03-scenarios' }, { text: 'Comparison', link: '/en/product/04-comparison' }] },
  { text: 'Features', collapsed: false, items: [{ text: 'Adaptive Scenes', link: '/en/features/01-scene-adaptive' }, { text: 'Three-Tier Models', link: '/en/features/02-models' }, { text: 'Diff Review', link: '/en/features/03-diff-review' }, { text: 'Preprocessing', link: '/en/features/04-preprocessing' }, { text: 'AI Refiner', link: '/en/features/05-ai-refiner' }, { text: 'Batch Pipeline', link: '/en/features/06-batch-pipeline' }, { text: 'Performance', link: '/en/features/07-performance' }, { text: 'Console', link: '/en/features/08-backend-console' }, { text: 'Export', link: '/en/features/09-export' }] },
  { text: 'Design', collapsed: false, items: [{ text: 'Brand Spirit', link: '/en/design/01-brand' }, { text: 'Three Colors', link: '/en/design/02-colors' }, { text: 'Typography', link: '/en/design/03-typography' }, { text: 'Layout', link: '/en/design/04-layout' }, { text: 'Components', link: '/en/design/05-components' }, { text: 'Themes', link: '/en/design/06-themes' }, { text: 'Visual Identity', link: '/en/design/07-visual' }] },
  { text: 'Development', collapsed: false, items: [{ text: 'Architecture', link: '/en/development/01-architecture' }, { text: 'Structure', link: '/en/development/02-structure' }, { text: 'Dev Environment', link: '/en/development/03-dev-env' }, { text: 'Model Management', link: '/en/development/04-model-mgmt' }, { text: 'OCR Engine', link: '/en/development/05-ocr-engine' }, { text: 'AI Refiner Dev', link: '/en/development/06-ai-refiner-dev' }, { text: 'Frontend Refactor', link: '/en/development/07-frontend-refactor' }, { text: 'Backend Console', link: '/en/development/08-backend-console-dev' }, { text: 'Contributing', link: '/en/development/09-contributing' }] },
  { text: 'Operations & Ecosystem', collapsed: false, items: [{ text: 'Auto Update', link: '/en/operations/01-auto-update' }, { text: 'Troubleshooting', link: '/en/operations/02-troubleshooting' }, { text: 'Cache Cleanup', link: '/en/operations/03-cache-cleanup' }, { text: 'Log Audit', link: '/en/operations/04-log-audit' }, { text: 'Open Source', link: '/en/ecosystem/01-open-source' }, { text: 'Community', link: '/en/ecosystem/02-community' }, { text: 'Roadmap', link: '/en/ecosystem/03-roadmap' }] },
]

const zhKeys = ['/', '/product/', '/quickstart/', '/features/', '/design/', '/development/', '/operations/', '/ecosystem/']
const enKeys = ['/en/', '/en/product/', '/en/quickstart/', '/en/features/', '/en/design/', '/en/development/', '/en/operations/', '/en/ecosystem/']

const sidebar = {}
zhKeys.forEach(k => sidebar[k] = zh)
enKeys.forEach(k => sidebar[k] = en)

export default sidebar
