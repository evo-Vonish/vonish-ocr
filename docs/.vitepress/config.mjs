import { defineConfig } from 'vitepress'
import sidebar from './sidebar.mjs'

export default defineConfig({
  base: '/reference/',
  title: 'VonishOCR',
  titleTemplate: ':title | 掌灯取证',
  description: '本地优先的 OCR 软件，让模糊与旧迹，再次清晰可读',
  lang: 'zh-CN',

  head: [
    ['link', { rel: 'preconnect', href: 'https://fonts.googleapis.com' }],
    ['link', { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' }],
    ['link', { href: 'https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=Noto+Sans+SC:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap', rel: 'stylesheet' }],
    ['link', { rel: 'icon', href: '/favicon.ico' }]
  ],

  themeConfig: {
    logo: '/logo.svg',
    siteTitle: 'VonishOCR',
    nav: [
      { text: '产品', link: '/product/01-introduction' },
      { text: '快速开始', link: '/quickstart/01-install' },
      { text: '功能手册', link: '/features/01-scene-adaptive' },
      { text: '设计系统', link: '/design/01-brand' },
      { text: '开发文档', link: '/development/01-architecture' },
      { text: 'GitHub', link: 'https://github.com/evo-Vonish/vonish-ocr' }
    ],

    sidebar,

    outline: {
      level: [2, 3],
      label: '本页目录'
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/evo-Vonish/vonish-ocr' }
    ],

    footer: {
      message: 'MIT License · 算力主权，光在手里',
      copyright: '© 2026 VonishOCR'
    },

    search: {
      provider: 'local',
      options: {
        translations: {
          button: {
            buttonText: '搜索文档',
            buttonAriaLabel: '搜索文档'
          },
          modal: {
            noResultsText: '未找到相关结果',
            resetButtonTitle: '清除',
            footer: {
              selectText: '选择',
              navigateText: '切换',
              closeText: '关闭'
            }
          }
        }
      }
    },

    darkModeSwitchLabel: '主题',
    lightModeSwitchTitle: '切换到浅色',
    darkModeSwitchTitle: '切换到深色',
    sidebarMenuLabel: '菜单',
    returnToTopLabel: '回到顶部',
    langMenuLabel: '语言'
  },

  markdown: {
    lineNumbers: true,
    config: (md) => {
      // 可扩展自定义 Markdown 语法
    }
  },

  vite: {
    css: {
      preprocessorOptions: {}
    }
  }
})
