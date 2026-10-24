import { mount } from 'svelte'
import '@fontsource-variable/archivo'
import './app.css'
import App from './App.svelte'

const target = document.getElementById('app')

if (import.meta.env.MODE === 'web') {
  // web: sign in first, then load the collection from Supabase (src/web/db.js)
  const { sb, open } = await import('./web/db.js')
  const { data } = await sb.auth.getSession()
  if (data.session) {
    await open(data.session.user.id)
    await import('./lib/theme.js')
    mount(App, { target })
  } else {
    const { default: Login } = await import('./lib/Login.svelte')
    mount(Login, { target })
  }
} else {
  await import('./lib/theme.js')
  mount(App, { target })
}
