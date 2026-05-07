import { defineConfig } from 'vitepress'

export default defineConfig({
  base: '/reference/',

  locales: {
    root: {
      label: '简体中文',
      lang: 'zh-CN',
      title: 'VonishOCR',
      titleTemplate: ':title | 掌灯取证',
      description: '本地优先的 OCR 软件，让模糊与旧迹，再次清晰可读',
      themeConfig: {
        siteTitle: 'VonishOCR',
        nav: [
          { text: 'GitHub', link: 'https://github.com/evo-Vonish/vonish-ocr' }
        ],
        outline: { level: [2, 3], label: '本页目录' },
        footer: {
          message: 'MIT License · 算力主权，光在手里',
          copyright: '© 2026 VonishOCR'
        },
        darkModeSwitchLabel: '主题',
        lightModeSwitchTitle: '切换到浅色',
        darkModeSwitchTitle: '切换到深色',
        sidebarMenuLabel: '菜单',
        returnToTopLabel: '回到顶部',
        langMenuLabel: '语言',
      }
    },
    en: {
      label: 'English',
      lang: 'en-US',
      title: 'VonishOCR',
      titleTemplate: ':title | Lantern in Hand',
      description: 'Local-first OCR. Hold the light in your own hand.',
      themeConfig: {
        siteTitle: 'VonishOCR',
        nav: [
          { text: 'GitHub', link: 'https://github.com/evo-Vonish/vonish-ocr' }
        ],
        outline: { level: [2, 3], label: 'On this page' },
        footer: {
          message: 'MIT License · The light is in your hand',
          copyright: '© 2026 VonishOCR'
        },
        darkModeSwitchLabel: 'Theme',
        lightModeSwitchTitle: 'Switch to Light',
        darkModeSwitchTitle: 'Switch to Dark',
        sidebarMenuLabel: 'Menu',
        returnToTopLabel: 'Back to top',
        langMenuLabel: 'Language',
      }
    }
  },

  head: [
    ['link', { rel: 'preconnect', href: 'https://fonts.googleapis.com' }],
    ['link', { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' }],
    ['link', { href: 'https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=Noto+Sans+SC:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap', rel: 'stylesheet' }],
    ['link', { rel: 'icon', href: '/favicon.ico' }]
  ],

  themeConfig: {
    logo: '/logo.svg',
    socialLinks: [
      { icon: 'github', link: 'https://github.com/evo-Vonish/vonish-ocr' }
    ],
    search: {
      provider: 'local',
      options: {
        translations: {
          button: { buttonText: '搜索文档', buttonAriaLabel: '搜索文档' },
          modal: {
            noResultsText: '未找到相关结果',
            resetButtonTitle: '清除',
            footer: { selectText: '选择', navigateText: '切换', closeText: '关闭' }
          }
        }
      }
    },
  },

  markdown: {
    lineNumbers: true,
  },

  vite: {
    css: { preprocessorOptions: {} }
  }
})
