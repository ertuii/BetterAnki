import { api } from './api.js'

// 'system' | 'light' | 'dark' -> data-theme on <html>, which app.css and the card frame read.
const media = matchMedia('(prefers-color-scheme: dark)')
let choice = 'system'

export function applyTheme(t = choice) {
  choice = t
  document.documentElement.dataset.theme = t === 'system' ? (media.matches ? 'dark' : 'light') : t
}

media.addEventListener('change', () => applyTheme())
applyTheme()
api.theme().then(applyTheme)
