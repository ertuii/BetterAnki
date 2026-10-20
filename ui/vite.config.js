import { cpSync } from 'node:fs'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig } from 'vite'

const outDir = '../src/muisti/web'

export default defineConfig({
  plugins: [
    svelte(),
    // formulas in cards: the sandboxed card frame loads KaTeX as plain files from /katex/
    { name: 'katex', closeBundle: () => cpSync('node_modules/katex/dist', `${outDir}/katex`, { recursive: true }) },
  ],
  build: { outDir, emptyOutDir: true },
})
