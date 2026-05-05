export default {
  '/product/': [
    {
      text: '产品',
      items: [
        { text: '产品介绍', link: '/product/introduction' },
        { text: '产品形态', link: '/product/morphology' },
        { text: '场景指南', link: '/product/scenarios' },
        { text: '竞品对比', link: '/product/comparison' }
      ]
    }
  ],
  '/quickstart/': [
    {
      text: '快速开始',
      items: [
        { text: '安装与启动', link: '/quickstart/install' },
        { text: '首次识别', link: '/quickstart/first-ocr' },
        { text: '批量处理', link: '/quickstart/batch' },
        { text: '本地 API 调用', link: '/quickstart/local-api' }
      ]
    }
  ],
  '/features/': [
    {
      text: '功能手册',
      collapsed: false,
      items: [
        { text: '场景自适应', link: '/features/scene-adaptive' },
        { text: '三档模型', link: '/features/models' },
        { text: 'Diff 复核', link: '/features/diff-review' },
        { text: '预处理引擎', link: '/features/preprocessing' },
        { text: 'AI 精修', link: '/features/ai-refiner' },
        { text: '批量流水线', link: '/features/batch-pipeline' },
        { text: '性能模式', link: '/features/performance' },
        { text: '后端控制台', link: '/features/backend-console' },
        { text: '导出与保存', link: '/features/export' }
      ]
    }
  ],
  '/design/': [
    {
      text: '设计系统',
      items: [
        { text: '品牌精神', link: '/design/brand' },
        { text: '三色成规', link: '/design/colors' },
        { text: '字体与排版', link: '/design/typography' },
        { text: '布局架构', link: '/design/layout' },
        { text: '组件规范', link: '/design/components' },
        { text: '主题系统', link: '/design/themes' },
        { text: '海报与视觉', link: '/design/visual' }
      ]
    }
  ],
  '/development/': [
    {
      text: '开发文档',
      collapsed: false,
      items: [
        { text: '技术架构', link: '/development/architecture' },
        { text: '目录结构', link: '/development/structure' },
        { text: '本地开发环境', link: '/development/dev-env' },
        { text: '模型管理', link: '/development/model-mgmt' },
        { text: 'OCR 引擎', link: '/development/ocr-engine' },
        { text: 'AI Refiner', link: '/development/ai-refiner-dev' },
        { text: '前端重构', link: '/development/frontend-refactor' },
        { text: '后端控制台开发', link: '/development/backend-console-dev' },
        { text: '贡献指南', link: '/development/contributing' }
      ]
    }
  ],
  '/operations/': [
    {
      text: '运维与部署',
      items: [
        { text: '自动更新', link: '/operations/auto-update' },
        { text: '诊断与排错', link: '/operations/troubleshooting' },
        { text: '模型缓存清理', link: '/operations/cache-cleanup' },
        { text: '日志审计', link: '/operations/log-audit' }
      ]
    }
  ],
  '/ecosystem/': [
    {
      text: '生态',
      items: [
        { text: '开源生态', link: '/ecosystem/open-source' },
        { text: '社区', link: '/ecosystem/community' },
        { text: '路线图', link: '/ecosystem/roadmap' }
      ]
    }
  ]
}
