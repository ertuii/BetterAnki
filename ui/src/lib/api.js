// Bridge to Python (pywebview js_api = Core). Every call returns a Promise.
const pw = () => /** @type {any} */ (window).pywebview

const ready = new Promise((resolve) => {
  if (pw()?.api) resolve()
  else window.addEventListener('pywebviewready', resolve, { once: true })
})

/** @type {any} */
export const api = new Proxy({}, {
  get: (_, name) => async (...args) => {
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
