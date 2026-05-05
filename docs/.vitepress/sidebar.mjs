export default {
  '/product/': [
    {
      text: '产品',
      items: [
        { text: '产品介绍', link: '/product/01-introduction' },
        { text: '产品形态', link: '/product/02-morphology' },
        { text: '场景指南', link: '/product/03-scenarios' },
        { text: '竞品对比', link: '/product/04-comparison' }
      ]
    }
  ],
  '/quickstart/': [
    {
      text: '快速开始',
      items: [
        { text: '安装与启动', link: '/quickstart/01-install' },
        { text: '首次识别', link: '/quickstart/02-first-ocr' },
        { text: '批量处理', link: '/quickstart/03-batch' },
        { text: '本地 API 调用', link: '/quickstart/04-local-api' }
      ]
    }
  ],
  '/features/': [
    {
      text: '功能手册',
      collapsed: false,
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
    }
  ],
  '/design/': [
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
    }
  ],
  '/development/': [
    {
      text: '开发文档',
      collapsed: false,
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
    }
  ],
  '/operations/': [
    {
      text: '运维与部署',
      items: [
        { text: '自动更新', link: '/operations/01-auto-update' },
        { text: '诊断与排错', link: '/operations/02-troubleshooting' },
        { text: '模型缓存清理', link: '/operations/03-cache-cleanup' },
        { text: '日志审计', link: '/operations/04-log-audit' }
      ]
    }
  ],
  '/ecosystem/': [
    {
      text: '生态',
      items: [
        { text: '开源生态', link: '/ecosystem/01-open-source' },
        { text: '社区', link: '/ecosystem/02-community' },
        { text: '路线图', link: '/ecosystem/03-roadmap' }
      ]
    }
  ]
}
