import { cpSync, readFileSync, writeFileSync } from 'node:fs'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig } from 'vite'

// one version for app and web: the one in src/muisti/__init__.py (a release tag is v<this>)
const version = /__version__ = "([^"]+)"/.exec(readFileSync('../src/muisti/__init__.py', 'utf8'))[1]

// desktop: served by src/muisti/server.py; web (vite build --mode web): deployed by Vercel, see vercel.json
export default defineConfig(({ mode }) => {
  const outDir = mode === 'web' ? 'dist-web' : '../src/muisti/web'
  return {
    plugins: [
      svelte(),
      {
        name: 'files',
        closeBundle: () => {
          // formulas in cards: the sandboxed card frame loads KaTeX as plain files from /katex/
          cpSync('node_modules/katex/dist', `${outDir}/katex`, { recursive: true })
          // open tabs compare this with their own version and offer a reload (web/core.js check_update)
          if (mode === 'web') {
            writeFileSync(`${outDir}/version.json`, JSON.stringify({ version }))
            // Vercel serves the folder as is: never cache the entry points, hashed assets forever
            writeFileSync(`${outDir}/vercel.json`, JSON.stringify({
              headers: [
                { source: '/(index.html|version.json)?', headers: [{ key: 'Cache-Control', value: 'no-store' }] },
                { source: '/assets/(.*)', headers: [{ key: 'Cache-Control', value: 'public, max-age=31536000, immutable' }] },
              ],
            }))
          }
        },
      },
    ],
    define: { 'import.meta.env.VITE_APP_VERSION': JSON.stringify(version) },
    build: { outDir, emptyOutDir: true },
  }
})
