<script>
  // Renders card HTML/CSS (user content) isolated in a sandboxed iframe without same-origin,
  // so card scripts can't reach the app API. Media resolves from /media/. Keys are forwarded via postMessage.
  let { html, css, ord = 0, onkey = null } = $props()

  let frame = $state()
  const dark = matchMedia('(prefers-color-scheme: dark)').matches

  const srcdoc = $derived(`<!doctype html><html><head><meta charset="utf-8">
<base href="${location.origin}/media/">
<style>
  html,body{margin:0;min-height:100%}
  body{padding:56px 40px;font-family:system-ui,sans-serif;font-size:20px;line-height:1.5}
  .card.nightMode{color:#ecebe6;background-color:#222326}
  img{max-width:100%;height:auto}
  hr#answer{border:0;border-top:1px solid #8884;margin:28px 0}
  audio{display:block;margin:12px auto}
  .ba-tts{border:1px solid #8886;background:transparent;color:inherit;border-radius:8px;padding:4px 8px;cursor:pointer;vertical-align:middle}
</style><style>${css}</style>
<script>
  addEventListener('keydown', (e) => parent.postMessage({ key: e.key, meta: e.metaKey || e.ctrlKey }, '*'))
  addEventListener('load', () => document.getElementById('answer')?.scrollIntoView())
  const say = (b) => { speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(b.dataset.text); u.lang = b.dataset.lang; speechSynthesis.speak(u) }
  addEventListener('click', (e) => { const b = e.target.closest('.ba-tts'); if (b) say(b) })
  addEventListener('load', () => document.querySelectorAll('.ba-tts[data-auto="1"]').forEach(say))
<\/script></head>
<body class="card card${ord + 1}${dark ? ' nightMode night_mode' : ''}">${html}</body></html>`)

  function onMessage(e) {
    if (!onkey || e.source !== frame?.contentWindow || typeof e.data?.key !== 'string') return
    onkey({ key: e.data.key, metaKey: e.data.meta, ctrlKey: false, preventDefault() {} })
  }
</script>

<svelte:window onmessage={onMessage} />

<iframe bind:this={frame} title="Karte" {srcdoc} sandbox="allow-scripts" allow="autoplay"></iframe>

<style>
  iframe { display: block; width: 100%; height: 100%; border: 0; background: #fff; }
  @media (prefers-color-scheme: dark) { iframe { background: #222326; } }
</style>
