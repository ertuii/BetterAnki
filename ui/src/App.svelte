<script>
  import { CalendarDays, Plus, Search, Download, ChartColumn, Shapes, Settings as Gear, Inbox as InboxIcon, GraduationCap } from '@lucide/svelte'
  import { api, flatten, hueFor, total } from './lib/api.js'
  import Today from './lib/Today.svelte'
  import Study from './lib/Study.svelte'
  import Editor from './lib/Editor.svelte'
  import Browser from './lib/Browser.svelte'
  import Stats from './lib/Stats.svelte'
  import DeckOptions from './lib/DeckOptions.svelte'
  import NoteTypes from './lib/NoteTypes.svelte'
  import Settings from './lib/Settings.svelte'
  import ImportDialog from './lib/ImportDialog.svelte'
  import Inbox from './lib/Inbox.svelte'
  import Exams from './lib/Exams.svelte'

  const mac = new URLSearchParams(location.search).has('mac') // title bar hidden, see app.py
  let view = $state(/** @type {any} */ ({ name: 'today' }))
  let decks = $state([])
  let overview = $state(null)
  let toast = $state(null)
  let toastTimer
  let update = $state(null)
  let updating = $state(false)

  const flat = $derived(flatten(decks))

  const checkUpdate = (manual = false) => api.check_update(manual).then((u) => (update = u))
  checkUpdate().catch(() => {})
  api.update_failure().then((why) => why && notify(`Update fehlgeschlagen, die bisherige Version läuft weiter: ${why}`, true))

  async function installUpdate() {
    updating = true
    try {
      await api.install_update() // the app closes and restarts itself in the new version
    } catch (e) {
      updating = false
      notify(String(e?.message ?? e), true)
    }
  }

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

  let importing = $state(null) // path of the file in the import dialog
  let dragging = $state(false)

  async function importFile() {
    try {
      const path = await api.pick_import_file()
      if (path) importing = path
    } catch (e) {
      notify(String(e?.message ?? e), true)
    }
  }

  // app.py calls this when a file is dropped onto the window
  /** @type {any} */ (window).__baImport = (path) => {
    dragging = false
    importing = path
  }

  async function prelearn(daysAhead) {
    const r = await run(() => api.prelearn(daysAhead))
    if (r) go('study', { deckId: r.deck_id, deckName: r.name, temporary: true })
  }

  async function practice(kind, name) {
    const r = await run(() => api.practice(kind, name))
    if (r) go('study', { deckId: r.deck_id, deckName: r.name, temporary: true })
  }

  const studyPlan = (minutes) => go('study', { plan: true, minutes, deckName: 'Lernplan' })

  function go(name, extra = {}) {
    view = { name, ...extra }
    if (name === 'today') refresh()
  }

  refresh()
  ;/** @type {any} */ (window).__baRefresh = refresh // app.py calls this after Claude changed something
  // Claude may add cards via MCP while the app is open; pick them up when the window regains focus.
  window.addEventListener('focus', () => view.name === 'today' && refresh())
</script>

{#if mac}<div class="titlebar pywebview-drag-region" aria-hidden="true"></div>{/if}
<div class="shell" class:mac class:studying={view.name === 'study'}>
  <aside>
    <div class="brand"><img src="/icon.svg" alt="" width="28" height="28" />BetterAnki</div>
    <nav>
      <button class="nav" class:on={view.name === 'today'} onclick={() => go('today')}><CalendarDays size={17} />Heute</button>
      <button class="nav" class:on={view.name === 'add'} onclick={() => go('add')}><Plus size={17} />Hinzufügen</button>
      <button class="nav" class:on={view.name === 'browse'} onclick={() => go('browse')}><Search size={17} />Browser</button>
      <button class="nav" class:on={view.name === 'stats'} onclick={() => go('stats')}><ChartColumn size={17} />Statistik</button>
      {#if overview?.features.exams}
        <button class="nav" class:on={view.name === 'exams'} onclick={() => go('exams')}><GraduationCap size={17} />Prüfungen</button>
      {/if}
      {#if overview?.inbox || view.name === 'inbox'}
        <button class="nav" class:on={view.name === 'inbox'} onclick={() => go('inbox')}>
          <InboxIcon size={17} />Eingang<span class="count num badge">{overview?.inbox || ''}</span>
        </button>
      {/if}
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
    {#if update}
      <div class="update" role="status">
        <b>Version {update.version} ist da</b>
        <button class="sm" disabled={updating} onclick={installUpdate}>{updating ? 'Lade Update …' : 'Aktualisieren'}</button>
      </div>
    {/if}
    <button class="nav foot" class:on={view.name === 'notetypes'} onclick={() => go('notetypes')}><Shapes size={17} />Notiztypen</button>
    <button class="nav foot" class:on={view.name === 'settings'} onclick={() => go('settings')}><Gear size={17} />Einstellungen</button>
    <button class="nav foot" onclick={importFile}><Download size={17} />Importieren</button>
  </aside>

  <main>
    {#if view.name === 'today'}
      <Today {decks} {flat} {overview} {run} {notify} onPlan={studyPlan} onInbox={() => go('inbox')} onOptions={(d) => go('options', { deckId: d.id })} onPrelearn={prelearn} onStudy={(d) => go('study', { deckId: d.id, deckName: d.name })} onAdd={() => go('add')} />
    {:else if view.name === 'study'}
      <Study deckId={view.deckId} deckName={view.deckName} temporary={view.temporary} plan={view.plan} minutes={view.minutes} {flat} {notify} onExit={() => go('today')} />
    {:else if view.name === 'add'}
      <div class="page"><h1>Karten hinzufügen</h1><Editor {flat} {notify} onSaved={refresh} /></div>
    {:else if view.name === 'browse'}
      <Browser {flat} {run} {notify} />
    {:else if view.name === 'notetypes'}
      <NoteTypes {notify} />
    {:else if view.name === 'settings'}
      <Settings {notify} {refresh} {checkUpdate} />
    {:else if view.name === 'exams' && overview}
      <Exams {flat} {overview} {run} {notify} />
    {:else if view.name === 'inbox'}
      <Inbox {flat} {notify} {refresh} />
    {:else if view.name === 'stats'}
      <Stats {flat} {notify} weak={overview?.features.weak} onPractice={practice} />
    {:else if view.name === 'options'}
      {#key view.deckId}<DeckOptions deckId={view.deckId} {notify} onBack={() => go('today')} />{/key}
    {/if}
  </main>
</div>

{#if importing}
  <ImportDialog path={importing} {flat} {notify} onDone={() => { importing = null; refresh() }} onClose={() => (importing = null)} />
{/if}

<svelte:window
  ondragover={(e) => { if (!e.dataTransfer?.types.includes('Files')) return; e.preventDefault(); dragging = true }}
  ondragleave={(e) => !e.relatedTarget && (dragging = false)}
  ondrop={(e) => { e.preventDefault(); dragging = false }} />

{#if dragging}
  <div class="drop" aria-hidden="true"><div>Zum Importieren loslassen<span>.apkg, .colpkg oder CSV</span></div></div>
{/if}

{#if toast}
  <div class="toast" class:error={toast.error} role="status">{toast.text}</div>
{/if}

<style>
  .shell { display: grid; grid-template-columns: 248px 1fr; height: 100%; transition: grid-template-columns 240ms var(--ease); }
  .shell.studying { grid-template-columns: 0 1fr; }
  /* macOS without title bar: the window buttons sit above the rail, the strip on top moves the window */
  .titlebar { position: fixed; top: 0; left: 0; right: 0; height: 28px; z-index: 15; }
  .mac aside { padding-top: 48px; }
  .mac main { padding-top: 28px; }
  .shell.studying aside { opacity: 0; pointer-events: none; }
  aside {
    border-right: 1px solid var(--rule);
    padding: 24px 14px 16px;
    display: flex; flex-direction: column; gap: 2px;
    overflow: hidden auto; transition: opacity 200ms var(--ease);
  }
  .brand { font-weight: 800; font-size: 18px; letter-spacing: -0.02em; padding: 0 10px 22px 4px; display: flex; align-items: center; gap: 8px; }
  .brand img { margin: -3px; }
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
  .update { margin: 8px 0 10px; padding: 12px; border-radius: var(--radius); background: var(--paper-2); display: flex; flex-direction: column; gap: 8px; font-size: 13px; }
  .badge { color: var(--paper); background: var(--ink); border-radius: 99px; padding: 0 7px; font-size: 12px; }
  .badge:empty { display: none; }
  .foot { color: var(--ink-2); }
  .foot.on { color: var(--ink); }
  main { overflow: auto; min-width: 0; }
  .page { padding: 32px 40px; max-width: 880px; display: flex; flex-direction: column; gap: 24px; }
  h1 { font-size: 26px; font-weight: 750; letter-spacing: -0.02em; }
  .toast {
    position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
    background: var(--ink); color: var(--paper); padding: 10px 16px; border-radius: var(--radius);
    font-weight: 500; box-shadow: 0 6px 24px rgb(0 0 0 / 0.18); max-width: 70ch;
    animation: rise 220ms var(--ease);
  }
  .drop { position: fixed; inset: 12px; border: 2px dashed var(--ink-2); border-radius: 16px; background: color-mix(in srgb, var(--paper) 88%, transparent); display: grid; place-items: center; z-index: 40; pointer-events: none; }
  .drop div { font-size: 22px; font-weight: 700; display: flex; flex-direction: column; align-items: center; gap: 6px; }
  .drop span { font-size: 14px; font-weight: 500; color: var(--ink-2); }
  .toast.error { background: var(--m-red); color: #fff; }
  @keyframes rise { from { transform: translate(-50%, 8px); opacity: 0; } }
</style>
