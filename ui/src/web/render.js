// Anki's card templates in JS, for the web app (the desktop uses Anki's own renderer, see core.py _render).
// Output matches what Core.next_card() hands the UI: [[type:…]] markers, audio tags and TTS buttons included.

const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
export const stripHtml = (s) => {
  const t = String(s).replace(/<style[\s\S]*?<\/style>|<script[\s\S]*?<\/script>|\[sound:[^\]]+\]/g, '').replace(/<[^>]+>/g, ' ')
  const el = document.createElement('textarea') // html entities
  el.innerHTML = t
  return el.value.replace(/[⁨⁩]/g, '').replace(/\s+/g, ' ').trim()
}
const empty = (v) => !String(v ?? '').replace(/<br\s*\/?>|<div>|<\/div>|&nbsp;|\s/gi, '')

const SPEAKER = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
  'stroke-linecap="round" stroke-linejoin="round"><path d="M11 5 6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/>' +
  '<path d="M19 5a10 10 0 0 1 0 14"/></svg>'

// {{c1::text::hint}}, nested ones too, and image occlusion's {{c1::image-occlusion:rect:left=.1:…}}
function parseCloze(text) {
  const root = { kids: [] }
  const stack = [root]
  const re = /\{\{c(\d+)::|\}\}/g
  let last = 0
  for (let m; (m = re.exec(text));) {
    const top = stack[stack.length - 1]
    if (m[1]) {
      top.kids.push(text.slice(last, m.index))
      const node = { n: Number(m[1]), kids: [] }
      top.kids.push(node)
      stack.push(node)
    } else if (stack.length > 1) { // "}}" closing a cloze; others are plain text
      top.kids.push(text.slice(last, m.index))
      stack.pop()
    } else top.kids.push(text.slice(last, m.index + 2))
    last = re.lastIndex
  }
  stack[stack.length - 1].kids.push(text.slice(last))
  // the hint: "::" in the cloze's own text (not in a nested one)
  const hint = (node) => {
    for (const [i, k] of node.kids.entries()) {
      if (typeof k !== 'string') continue
      const at = k.indexOf('::')
      if (at >= 0) {
        node.hint = [k.slice(at + 2), ...node.kids.slice(i + 1).map((x) => (typeof x === 'string' ? x : ''))].join('')
        node.kids = [...node.kids.slice(0, i), k.slice(0, at)]
        break
      }
    }
    node.kids.forEach((k) => typeof k !== 'string' && hint(k))
  }
  root.kids.forEach((k) => typeof k !== 'string' && hint(k))
  return root.kids
}

export function clozeNumbers(text) {
  const out = []
  const walk = (kids) => kids.forEach((k) => typeof k !== 'string' && (out.push(k.n), walk(k.kids)))
  walk(parseCloze(String(text)))
  return out
}

function occlusion(body, cls, n) {
  const [, shape, ...props] = body.split(':')
  const attrs = props.map((p) => {
    const [k, v] = p.split('=')
    return k === 'oi' ? `data-occludeInactive="${esc(v)}"` : `data-${k}="${esc(v)}"`
  })
  return `<div class="${cls}" data-ordinal="${n}" data-shape="${esc(shape)}" ${attrs.join(' ')} ></div>`
}

function cloze(text, ord, side) {
  const render = (kids) => kids.map((k) => {
    if (typeof k === 'string') return k
    const body = render(k.kids)
    const active = k.n === ord
    if (body.startsWith('image-occlusion:')) return occlusion(body, active ? (side === 'q' ? 'cloze' : 'cloze-highlight') : 'cloze-inactive', k.n)
    if (!active) return `<span class="cloze-inactive" data-ordinal="${k.n}">${body}</span>`
    if (side === 'a') return `<span class="cloze" data-ordinal="${k.n}">${body}</span>`
    return `<span class="cloze" data-cloze="${esc(body)}" data-ordinal="${k.n}">[${k.hint ?? '...'}]</span>`
  }).join('')
  return render(parseCloze(String(text)))
}

/** The active cloze's texts (nested clozes as plain text), for {{cloze-only:}} and typing in a cloze. */
export function clozeTexts(text, ord) {
  const flat = (kids) => kids.map((k) => (typeof k === 'string' ? k : flat(k.kids))).join('')
  const out = []
  const walk = (kids) => kids.forEach((k) => typeof k !== 'string' && (k.n === ord && out.push(flat(k.kids)), walk(k.kids)))
  walk(parseCloze(String(text)))
  return out
}

let hintId = 0
const FILTERS = {
  text: (v) => stripHtml(v),
  hint: (v, name) => {
    const id = `hint${(++hintId).toString(16)}`
    return `<a class=hint href="#"\nonclick="this.style.display='none';\ndocument.getElementById('${id}').style.display='block';\nreturn false;" draggable=false>\n${esc(name)}</a>\n<div id="${id}" class=hint style="display: none">${v}</div>\n`
  },
  cloze: (v, _, ctx) => cloze(v, ctx.ord + 1, ctx.side),
  'cloze-only': (v, _, ctx) => clozeTexts(v, ctx.ord + 1).join(', '),
}

function field(spec, ctx) {
  const parts = spec.split(':')
  if (parts[0].startsWith('tts ')) { // {{tts de_DE:Field}}
    const lang = parts[0].slice(4).split(' ')[0]
    return `[anki:tts lang=${lang}]${stripHtml(ctx.fields[parts.slice(1).join(':')] ?? '')}[/anki:tts]`
  }
  if (parts[0] === 'type') return `[[${spec}]]` // handled after rendering, like Anki
  const name = parts.pop()
  let v
  if (name === 'FrontSide') v = ctx.frontSide ?? ''
  else if (name === 'Tags') v = ctx.tags.join(' ')
  else if (name === 'Deck') v = ctx.deck
  else if (name === 'Subdeck') v = ctx.deck.split('::').pop()
  else if (name === 'Card') v = ctx.cardName
  else if (name === 'Type') v = ctx.typeName
  else if (name in ctx.fields) v = ctx.fields[name]
  else return `{unbekanntes Feld ${esc(name)}}`
  for (const f of parts.reverse()) v = FILTERS[f] ? FILTERS[f](v, name, ctx) : v
  return v
}

/** Mustache-like: {{#F}}…{{/F}}, {{^F}}…{{/F}}, {{filter:F}}. */
function render(tmpl, ctx) {
  const tokens = String(tmpl).split(/(\{\{[^}]+\}\})/)
  const out = []
  const stack = [] // [name, show]
  const visible = () => stack.every((s) => s[1])
  for (const t of tokens) {
    const m = /^\{\{\s*([#^/]?)\s*([^}]+?)\s*\}\}$/.exec(t)
    if (!m) { if (visible()) out.push(t); continue }
    const [, kind, name] = m
    if (kind === '#' || kind === '^') {
      const has = name in ctx.fields ? !empty(ctx.fields[name]) : name === 'Tags' ? ctx.tags.length > 0 : false
      stack.push([name, kind === '#' ? has : !has])
    } else if (kind === '/') stack.pop()
    else if (visible()) out.push(field(name, ctx))
  }
  return out.join('')
}

/** Anki's av handling as in Core._render: [sound:x] → <audio>, tts → speaker button. */
function av(html, autoplay) {
  return html
    .replace(/\[sound:([^\]]+)\]/g, (_, f) => `<audio controls ${autoplay ? 'autoplay' : ''} src="${esc(f)}"></audio>`)
    .replace(/\[anki:tts lang=([^\]]+)\]([\s\S]*?)\[\/anki:tts\]/g, (_, lang, text) =>
      `<button class="ba-tts" data-auto="${autoplay ? 1 : 0}" data-lang="${esc(lang.replace('_', '-'))}" data-text="${esc(text)}" aria-label="Vorlesen">${SPEAKER}</button>`)
}

/** Question and answer HTML of a card. nt: Anki's legacy note type dict. */
export function renderCard({ ord, note, nt, deck, autoplay = true }) {
  const names = nt.flds.map((f) => f.name)
  const vals = note.flds.split('\x1f')
  const fields = Object.fromEntries(names.map((n, i) => [n, vals[i] ?? '']))
  const tmpl = nt.type === 1 ? nt.tmpls[0] : nt.tmpls[ord]
  const ctx = { fields, ord, side: 'q', tags: note.tags.trim().split(/\s+/).filter(Boolean), deck, cardName: tmpl.name, typeName: nt.name }
  const q = render(tmpl.qfmt, ctx)
  const a = render(tmpl.afmt, { ...ctx, side: 'a', frontSide: q.replace(/\[\[type:[^\]]+\]\]/g, '') })
  return { question: av(q, autoplay), answer: av(a, autoplay), css: nt.css, fields }
}

/** Anki's compare_answer output: typed vs expected, character diff. */
export function compareAnswer(expected, typed, combining = true) {
  let exp = stripHtml(expected)
  if (!combining) exp = exp.normalize('NFD').replace(/\p{M}/gu, '')
  exp = exp.normalize('NFC')
  typed = typed.normalize('NFC')
  if (exp === typed) return `<code id=typeans><span class=typeGood>${esc(exp)}</span></code>`
  // LCS on characters
  const a = [...typed], b = [...exp]
  const L = Array.from({ length: a.length + 1 }, () => new Array(b.length + 1).fill(0))
  for (let i = a.length - 1; i >= 0; i--) for (let j = b.length - 1; j >= 0; j--)
    L[i][j] = a[i] === b[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1])
  const top = [], bottom = []
  let i = 0, j = 0
  while (i < a.length || j < b.length) {
    if (i < a.length && j < b.length && a[i] === b[j]) { top.push(['typeGood', a[i]]); bottom.push(['typeGood', b[j]]); i++; j++ }
    else if (j < b.length && (i >= a.length || L[i][j + 1] >= L[i + 1][j])) bottom.push(['typeMissed', b[j++]])
    else top.push(['typeBad', a[i++]])
  }
  const spans = (xs) => {
    const out = []
    for (const [c, ch] of xs) {
      if (out.length && out[out.length - 1][0] === c) out[out.length - 1][1] += ch
      else out.push([c, ch])
    }
    return out.map(([c, s]) => `<span class=${c}>${esc(s)}</span>`).join('')
  }
  return `<code id=typeans>${spans(top)}<br><span id=typearrow>&darr;</span><br>${spans(bottom)}</code>`
}
