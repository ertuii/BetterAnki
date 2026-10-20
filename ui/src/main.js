import { mount } from 'svelte'
import '@fontsource-variable/archivo'
import './app.css'
import './lib/theme.js'
import App from './App.svelte'

export default mount(App, { target: document.getElementById('app') })
