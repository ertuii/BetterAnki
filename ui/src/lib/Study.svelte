<script>
  import { ArrowLeft, Pencil, Undo2 } from '@lucide/svelte'
  import { api } from './api.js'
  import Editor from './Editor.svelte'
  import CardFrame from './CardFrame.svelte'

  let { deckId, deckName, flat, notify, onExit } = $props()

  let card = $state(null)
  let done = $state(false)
  let revealed = $state(false)
  let editing = $state(false)
  let busy = false

  const BUTTONS = [
    { ease: 1, label: 'Nochmal', cls: 'again' },
    { ease: 2, label: 'Schwer', cls: 'hard' },
    { ease: 3, label: 'Gut', cls: 'good' },
    { ease: 4, label: 'Einfach', cls: 'easy' },
  ]

  async function next() {
    card = await api.next_card(deckId)
    revealed = false
    done = !card
  }

  function reveal() {
    revealed = true
  }

  async function answer(ease) {
    if (busy || !card) return
    busy = true
    try {
      await api.answer(card.card_id, ease)
      await next()
    } catch (e) {
      notify(String(e?.message ?? e), true)
    } finally {
      busy = false
    }
  }

  async function undo() {
    const name = await api.undo()
    notify(name ? `Rückgängig: ${name}` : 'Nichts rückgängig zu machen')
    await next()
  }

  async function bury() {
    await api.bury_card(card.card_id)
    notify('Karte bis morgen zurückgestellt')
    await next()
  }

  function onKey(e) {
    if (editing) return
    if ((e.metaKey || e.ctrlKey) && e.key === 'z') return e.preventDefault(), undo()
    if (e.key === 'Escape') return onExit()
    if (!card) return
    if (e.key === 'e') return (editing = true)
    if (e.key === '-') return bury()
    if (!revealed && (e.key === ' ' || e.key === 'Enter')) return e.preventDefault(), reveal()
    if (revealed && (e.key === ' ' || e.key === 'Enter')) return e.preventDefault(), answer(3)
    if (revealed && ['1', '2', '3', '4'].includes(e.key)) answer(Number(e.key))
  }

  next()
</script>

<svelte:window onkeydown={onKey} />

<div class="study">
  <header>
    <button class="plain" onclick={onExit}><ArrowLeft size={17} />{deckName} <kbd>Esc</kbd></button>
    {#if card}
      <div class="counts num" aria-label="Verbleibend">
        <span class="c-new" class:cur={card.queue === 0}>{card.counts.new}</span>
        <span class="c-learn" class:cur={card.queue === 1 || card.queue === 3}>{card.counts.learn}</span>
        <span class="c-review" class:cur={card.queue === 2}>{card.counts.review}</span>
      </div>
      <div class="tools">
        <button class="plain" onclick={undo} title="Rückgängig (⌘Z)"><Undo2 size={17} /></button>
        <button class="plain" onclick={() => (editing = true)} title="Bearbeiten (E)"><Pencil size={17} /></button>
      </div>
    {/if}
  </header>

  {#if done}
    <div class="done">
      <h1>Fertig für heute.</h1>
      <p class="muted">In „{deckName}“ ist gerade nichts mehr fällig. Lernkarten kommen nach ihrer Lernstufe zurück.</p>
      <div class="row">
        <button onclick={onExit}>Zur Übersicht</button>
        <button class="ghost" onclick={undo}>Letzte Antwort rückgängig</button>
      </div>
    </div>
  {:else if card}
    <div class="card-area">
      <CardFrame html={revealed ? card.answer : card.question} css={card.css} ord={card.ord} onkey={onKey} />
    </div>
    <footer>
      {#if !revealed}
        <button class="reveal" onclick={reveal}>Antwort zeigen <kbd class="inv">Leertaste</kbd></button>
      {:else}
        <div class="answers">
          {#each BUTTONS as b, i}
            <button class="ans {b.cls}" onclick={() => answer(b.ease)}>
              <span class="ivl num">{card.buttons[i]}</span>
              <span>{b.label}</span>
              <kbd>{b.ease}</kbd>
            </button>
          {/each}
        </div>
      {/if}
    </footer>
  {/if}
</div>

{#if editing && card}
  <div class="sheet-backdrop" onclick={(e) => e.target === e.currentTarget && (editing = false)} role="presentation">
    <div class="sheet" role="dialog" aria-label="Karte bearbeiten">
      <h2>Notiz bearbeiten</h2>
      <Editor noteId={card.note_id} {flat} {notify} onSaved={async () => { editing = false; card = await api.next_card(deckId) }} onCancel={() => (editing = false)} />
    </div>
  </div>
{/if}

<style>
  .study { height: 100%; display: flex; flex-direction: column; }
  header { display: flex; align-items: center; padding: 14px 20px; gap: 16px; }
  .counts { display: flex; gap: 14px; font-weight: 650; margin: 0 auto; font-size: 15px; }
  .counts span { padding-bottom: 2px; border-bottom: 2px solid transparent; }
  .counts .cur { border-bottom-color: currentColor; }
  .c-new { color: var(--new); } .c-learn { color: var(--learn); } .c-review { color: var(--review); }
  .tools { display: flex; gap: 4px; }
  .card-area { flex: 1; display: flex; justify-content: center; padding: 8px 32px 0; min-height: 0; }
  .card-area :global(iframe) {
    width: min(860px, 100%); border-radius: 14px 14px 0 0;
    box-shadow: 0 2px 4px rgb(0 0 0 / 0.04), 0 12px 40px rgb(0 0 0 / 0.08);
  }
  footer { display: flex; justify-content: center; padding: 20px 32px 28px; border-top: 1px solid var(--rule); }
  .reveal { height: 46px; padding: 0 28px; font-size: 15px; }
  kbd.inv { color: var(--paper); border-color: color-mix(in srgb, var(--paper) 40%, transparent); }
  .answers { display: grid; grid-template-columns: repeat(4, minmax(120px, 160px)); gap: 10px; }
  .ans {
    flex-direction: column; gap: 4px; height: auto; padding: 10px 12px; background: var(--paper);
    color: var(--ink); border: 1px solid var(--rule-2); font-weight: 650;
  }
  .ans:hover { background: var(--paper-2); opacity: 1; }
  .ivl { font-size: 13px; font-weight: 500; color: var(--ink-2); }
  .ans kbd { margin-top: 2px; }
  .again { border-bottom: 3px solid var(--m-red); }
  .hard { border-bottom: 3px solid var(--m-ochre); }
  .good { border-bottom: 3px solid var(--m-green); }
  .easy { border-bottom: 3px solid var(--m-blue); }
  .done { margin: auto; max-width: 52ch; display: flex; flex-direction: column; gap: 12px; padding: 32px; }
  .done h1 { font-size: 40px; font-weight: 800; letter-spacing: -0.03em; }
  .row { display: flex; gap: 8px; margin-top: 12px; }
  .sheet-backdrop { position: fixed; inset: 0; background: rgb(0 0 0 / 0.28); display: flex; justify-content: flex-end; z-index: 20; }
  .sheet { width: min(640px, 100%); height: 100%; background: var(--paper); padding: 28px 32px; overflow: auto; display: flex; flex-direction: column; gap: 20px; animation: slide 240ms var(--ease); }
  .sheet h2 { font-size: 20px; font-weight: 750; }
  @keyframes slide { from { transform: translateX(32px); opacity: 0; } }
</style>
