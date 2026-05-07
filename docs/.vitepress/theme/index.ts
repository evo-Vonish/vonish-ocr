import DefaultTheme from 'vitepress/theme'
import '../../../src/styles/theme-system.css'
import './custom.css'

if (typeof window !== 'undefined') {
  const params = new URLSearchParams(window.location.search)
  const style = params.get('themeStyle') || 'desk'
  const mode = params.get('themeMode') || 'dark'
  document.documentElement.dataset.themeStyle = ['desk', 'mono', 'hc'].includes(style) ? style : 'desk'
  document.documentElement.dataset.themeMode = ['dark', 'light'].includes(mode) ? mode : 'dark'
  document.documentElement.dataset.theme = `${document.documentElement.dataset.themeStyle}-${document.documentElement.dataset.themeMode}`
}

export default DefaultTheme
