// A subset of Anki's search syntax for the web browser: words and "quoted phrases" (in any field), deck:, tag:,
// note:, is:new|learn|review|due|suspended|buried, flag:N, prop:ivl/due/reps/lapses with < > =, -negation.
// All terms must match (AND). ponytail: no OR, no parentheses, no regex; the desktop has Anki's full search.
import { stripHtml } from './render.js'

const fold = (s) => s.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()
const glob = (pat) => new RegExp('^' + pat.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/_/g, '.') + '$', 'i')

function terms(q) {
  return [...q.matchAll(/(-?)(?:(\w+):)?(?:"([^"]*)"|(\S+))/g)].map(([, neg, key, quoted, word]) => ({
    neg: !!neg, key: key?.toLowerCase(), val: quoted ?? word,
  }))
}

function matcher({ key, val }, ctx) {
  const v = val.toLowerCase()
  if (key === 'deck') {
    const re = glob(val)
    return (c) => { const n = ctx.deckName(c.odid || c.did); return re.test(n) || n.toLowerCase().startsWith(v + '::') }
  }
  if (key === 'tag') {
    const re = glob(val)
    return (c, note) => note.tags.trim().split(/\s+/).some((t) => re.test(t) || t.toLowerCase().startsWith(v + '::'))
  }
  if (key === 'note') { const re = glob(val); return (c, note) => re.test(ctx.nt(note.mid)?.name ?? '') }
  if (key === 'flag') return (c) => (c.flags & 7) === Number(val)
  if (key === 'is') {
    return {
      new: (c) => c.type === 0, learn: (c) => c.queue === 1 || c.queue === 3, review: (c) => c.type === 2 || c.type === 3,
      due: (c) => ((c.queue === 2 || c.queue === 3) && c.due <= ctx.today) || (c.queue === 1 && c.due <= Date.now() / 1000),
      suspended: (c) => c.queue === -1, buried: (c) => c.queue === -2 || c.queue === -3,
    }[v] ?? (() => false)
  }
  if (key === 'prop') {
    const m = /^(ivl|due|reps|lapses|ease)(<=|>=|!=|=|<|>)(-?[\d.]+)$/.exec(val)
    if (!m) return () => false
    const [, prop, op, num] = m
    const get = { ivl: (c) => c.ivl, reps: (c) => c.reps, lapses: (c) => c.lapses, ease: (c) => c.factor / 1000,
      due: (c) => (c.queue === 2 || c.queue === 3 ? c.due - ctx.today : NaN) }[prop]
    const n = Number(num)
    const cmp = { '<': (a) => a < n, '>': (a) => a > n, '<=': (a) => a <= n, '>=': (a) => a >= n, '=': (a) => a === n, '!=': (a) => a !== n }[op]
    return (c) => cmp(get(c))
  }
  // plain text, also an unknown "key:value" (e.g. a field search) as text
  const text = fold(key ? `${key}:${val}` : val)
  const re = text.includes('*') || text.includes('_') ? new RegExp(text.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/_/g, '.')) : null
  return (c, note) => {
    const hay = fold(stripHtml(note.flds.replace(/\x1f/g, ' ')))
    return re ? re.test(hay) : hay.includes(text)
  }
}

/** Cards matching `query`, sorted by the notes' sort field like Anki's default browser order. */
export function search(query, ctx) {
  const tests = terms(query.trim()).map((t) => ({ neg: t.neg, fn: matcher(t, ctx) }))
  const out = []
  for (const c of ctx.S.cards.values()) {
    const note = ctx.S.notes.get(c.nid)
    if (note && tests.every(({ neg, fn }) => fn(c, note) !== neg)) out.push([note.sfld ?? '', c])
  }
  return out.sort((a, b) => String(a[0]).localeCompare(String(b[0]), 'de') || a[1].ord - b[1].ord).map(([, c]) => c)
}
