// Bridge to the core: Python via pywebview (js_api = Core) on the desktop, src/web/core.js in the web build
// (vite --mode web). Every call returns a Promise.
export const web = import.meta.env.MODE === 'web'
const webCore = web ? import('../web/core.js') : null // not in the desktop bundle
const pw = () => /** @type {any} */ (window).pywebview

const ready = web ? Promise.resolve() : new Promise((resolve) => {
  if (pw()?.api) resolve()
  else window.addEventListener('pywebviewready', resolve, { once: true })
})

/** @type {any} */
export const api = new Proxy({}, {
  get: (_, name) => async (...args) => {
    if (web) {
      const core = await webCore
      if (typeof core[name] !== 'function') throw new Error('Gibt es im Web noch nicht, nutze dafür die Desktop-App.')
      return core[name](...args)
    }
    await ready
    return pw().api[name](...args)
  },
})

// One fixed marker hue per top-level deck, derived from its id so it never shifts.
const HUES = ['red', 'blue', 'green', 'ochre', 'violet', 'teal', 'pink']
export const hueFor = (topId) => `var(--m-${HUES[Number(BigInt(topId) % 7n)]})`

// Deck tree -> flat rows with depth and the top-level id (for the hue).
export function flatten(decks, depth = 0, top = null, out = []) {
  for (const d of decks) {
    out.push({ ...d, depth, top: top ?? d.id })
    flatten(d.children, depth + 1, top ?? d.id, out)
  }
  return out
}

export const total = (d) => d.new + d.learn + d.review
