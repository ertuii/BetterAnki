<script>
  import { CalendarDays, Plus, Search, Download } from '@lucide/svelte'
  import { api, flatten, hueFor, total } from './lib/api.js'
  import Today from './lib/Today.svelte'
  import Study from './lib/Study.svelte'
  import Editor from './lib/Editor.svelte'
  import Browser from './lib/Browser.svelte'

  let view = $state({ name: 'today' })
  let decks = $state([])
  let overview = $state(null)
  let toast = $state(null)
  let toastTimer

  const flat = $derived(flatten(decks))

  async function refresh() {
    ;[decks, overview] = await Promise.all([api.decks(), api.overview()])
  }

  function notify(text, error = false) {
    toast = { text, error }
    clearTimeout(toastTimer)
    toastTimer = setTimeout(() => (toast = null), error ? 6000 : 2600)
  }

  // Wraps a Python call: shows the error instead of failing silently.
  async function run(fn, okText) {
    try {
      const r = await fn()
      if (okText) notify(typeof okText === 'function' ? okText(r) : okText)
      await refresh()
      return r
    } catch (e) {
      notify(String(e?.message ?? e), true)
    }
  }

  async function importFile() {
    const path = await api.pick_import_file()
    if (path) await run(() => api.import_file(path), (r) => `Importiert: ${r}`)
  }

  function go(name, extra = {}) {
    view = { name, ...extra }
    if (name === 'today') refresh()
  }

  refresh()
  // Claude may add cards via MCP while the app is open; pick them up when the window regains focus.
  window.addEventListener('focus', () => view.name === 'today' && refresh())
</script>

<div class="shell" class:studying={view.name === 'study'}>
  <aside>
    <div class="brand">BetterAnki</div>
    <nav>
      <button class="nav" class:on={view.name === 'today'} onclick={() => go('today')}><CalendarDays size={17} />Heute</button>
      <button class="nav" class:on={view.name === 'add'} onclick={() => go('add')}><Plus size={17} />Hinzufügen</button>
      <button class="nav" class:on={view.name === 'browse'} onclick={() => go('browse')}><Search size={17} />Browser</button>
    </nav>
    <div class="label">Stapel</div>
    <nav class="decks">
      {#each flat.filter((d) => d.depth === 0) as d (d.id)}
        <button class="nav" onclick={() => go('study', { deckId: d.id, deckName: d.name })} title="{d.name} lernen">
          <span class="chip" style:background={hueFor(d.top)}></span>
          <span class="name">{d.name}</span>
          <span class="count num">{total(d) || ''}</span>
        </button>
      {/each}
    </nav>
    <button class="nav foot" onclick={importFile}><Download size={17} />Importieren</button>
  </aside>

  <main>
    {#if view.name === 'today'}
      <Today {decks} {flat} {overview} {run} {notify} onStudy={(d) => go('study', { deckId: d.id, deckName: d.name })} onAdd={() => go('add')} />
    {:else if view.name === 'study'}
      <Study deckId={view.deckId} deckName={view.deckName} {flat} {notify} onExit={() => go('today')} />
    {:else if view.name === 'add'}
      <div class="page"><h1>Karten hinzufügen</h1><Editor {flat} {notify} onSaved={refresh} /></div>
    {:else if view.name === 'browse'}
      <Browser {flat} {run} {notify} />
    {/if}
  </main>
</div>

{#if toast}
  <div class="toast" class:error={toast.error} role="status">{toast.text}</div>
{/if}

<style>
  .shell { display: grid; grid-template-columns: 248px 1fr; height: 100%; transition: grid-template-columns 240ms var(--ease); }
  .shell.studying { grid-template-columns: 0 1fr; }
  .shell.studying aside { opacity: 0; pointer-events: none; }
  aside {
    border-right: 1px solid var(--rule);
    padding: 24px 14px 16px;
    display: flex; flex-direction: column; gap: 2px;
    overflow: hidden auto; transition: opacity 200ms var(--ease);
  }
  .brand { font-weight: 800; font-size: 18px; letter-spacing: -0.02em; padding: 0 10px 22px; }
  nav { display: flex; flex-direction: column; gap: 2px; }
  .nav {
    background: transparent; color: var(--ink); border: 0; font-weight: 500;
    padding: 8px 10px; width: 100%; justify-content: flex-start; text-align: left;
  }
  .nav:hover { background: var(--paper-2); opacity: 1; }
  .nav.on { background: var(--paper-3); font-weight: 650; }
  .nav :global(svg) { color: var(--ink-2); flex: none; }
  .label { font-size: 12px; color: var(--ink-2); margin: 22px 10px 6px; }
  .decks { flex: 1; }
  .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .count { margin-left: auto; color: var(--ink-2); font-size: 13px; font-weight: 500; }
  .foot { color: var(--ink-2); }
  main { overflow: auto; min-width: 0; }
  .page { padding: 32px 40px; max-width: 880px; display: flex; flex-direction: column; gap: 24px; }
  h1 { font-size: 26px; font-weight: 750; letter-spacing: -0.02em; }
  .toast {
    position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
    background: var(--ink); color: var(--paper); padding: 10px 16px; border-radius: var(--radius);
    font-weight: 500; box-shadow: 0 6px 24px rgb(0 0 0 / 0.18); max-width: 70ch;
    animation: rise 220ms var(--ease);
  }
  .toast.error { background: var(--m-red); color: #fff; }
  @keyframes rise { from { transform: translate(-50%, 8px); opacity: 0; } }
</style>
