<script>
  import { ArrowLeft, Pencil, Undo2, FastForward } from '@lucide/svelte'
  import { api } from './api.js'
  import Editor from './Editor.svelte'
  import CardFrame from './CardFrame.svelte'

  // temporary: a pre-learn/practice deck, removed again when the session ends
  // plan: the study plan across all decks (nearest exam first) for `minutes`
  let { deckId, deckName, flat, notify, onExit, temporary = false, plan = false, minutes = 0 } = $props()

  let card = $state(null)
  let done = $state(false)
  let revealed = $state(false)
  let editing = $state(false)
  let busy = false
  let prefs = $state({ show_remaining_due_counts: true, show_intervals_on_buttons: true, time_limit_secs: 0, hide_audio_play_buttons: false })
  let elapsed = $state(0) // seconds the current card has been shown
  let shownAt = Date.now()
  let autoAdvance = $state(false)
  let advanceTimer
  let boxStart = Date.now()
  let boxCount = 0
  const sessionStart = Date.now()
  let answered = $state(0)
  let timeUp = $state(false)
  // svelte-ignore state_referenced_locally
  let left = $state(minutes) // plan: minutes left, fixed per session

  const fetchCard = () => (plan ? api.plan_next() : api.next_card(deckId))

  api.preferences().then((p) => (prefs = p.reviewing))

  const tick = setInterval(() => {
    if (plan && minutes) left = Math.max(0, minutes - Math.floor((Date.now() - sessionStart) / 60000))
    if (!card || (revealed && card.study.stop_timer_on_answer)) return
    elapsed = Math.min(card.study.cap_secs, Math.floor((Date.now() - shownAt) / 1000))
  }, 1000)
  $effect(() => () => {
    clearInterval(tick)
    clearTimeout(advanceTimer)
  })
  const clock = (sec) => `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`

  // Anki's "auto advance": toggled with A, timings and actions come from the deck's preset.
  $effect(() => {
    clearTimeout(advanceTimer)
    if (!autoAdvance || !card) return
    const st = card.study
    // ponytail: wait_for_audio is ignored, the timer starts when the card is shown
    if (!revealed && st.seconds_question > 0) {
      advanceTimer = setTimeout(() => (st.question_action === 0 ? reveal() : notify('Zeit, die Antwort aufzudecken')), st.seconds_question * 1000)
    } else if (revealed && st.seconds_answer > 0) {
      const act = [() => bury(), () => answer(1), () => answer(3), () => answer(2), () => notify('Zeit, die Karte zu bewerten')][st.answer_action]
      advanceTimer = setTimeout(act, st.seconds_answer * 1000)
    }
  })

  async function exit() {
    clearTimeout(advanceTimer)
    if (temporary) await api.end_prelearn(deckId)
    onExit()
  }

  const BUTTONS = [
    { ease: 1, label: 'Nochmal', cls: 'again' },
    { ease: 2, label: 'Schwer', cls: 'hard' },
    { ease: 3, label: 'Gut', cls: 'good' },
    { ease: 4, label: 'Einfach', cls: 'easy' },
  ]

  async function next() {
    timeUp = plan && minutes > 0 && Date.now() - sessionStart >= minutes * 60000
    card = timeUp ? null : await fetchCard()
    revealed = false
    done = !card
    shownAt = Date.now()
    elapsed = 0
  }

  function reveal() {
    revealed = true
  }

  async function answer(ease) {
    if (busy || !card) return
    busy = true
    try {
      await api.answer(card.card_id, ease)
      boxCount++
      answered++
      if (prefs.time_limit_secs && Date.now() - boxStart >= prefs.time_limit_secs * 1000) {
        notify(`Zeitlimit erreicht: ${boxCount} Karten in ${Math.round((Date.now() - boxStart) / 60000)} Minuten`)
        boxStart = Date.now()
        boxCount = 0
      }
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
    if (e.key === 'Escape') return exit()
    if (!card) return
    if (e.key === 'a' || e.key === 'A') return toggleAuto()
    if (e.key === 'e') return (editing = true)
    if (e.key === '-') return bury()
    if (!revealed && (e.key === ' ' || e.key === 'Enter')) return e.preventDefault(), reveal()
    if (revealed && (e.key === ' ' || e.key === 'Enter')) return e.preventDefault(), answer(3)
    if (revealed && ['1', '2', '3', '4'].includes(e.key)) answer(Number(e.key))
  }

  function toggleAuto() {
    if (!card.study.seconds_question && !card.study.seconds_answer) return notify('„Automatisch weiter“ ist in den Stapel-Optionen nicht eingestellt')
    autoAdvance = !autoAdvance
    notify(autoAdvance ? 'Automatisch weiter: an' : 'Automatisch weiter: aus')
  }

  next()
</script>

<svelte:window onkeydown={onKey} />

<div class="study">
  <header>
    <button class="plain" onclick={exit}><ArrowLeft size={17} />{deckName}{plan && card ? ` · ${card.deck}` : ''} <kbd>Esc</kbd></button>
    {#if card}
      <div class="mid">
        {#if prefs.show_remaining_due_counts}
          <div class="counts num" aria-label="Verbleibend">
            <span class="c-new" class:cur={card.queue === 0}>{card.counts.new}</span>
            <span class="c-learn" class:cur={card.queue === 1 || card.queue === 3}>{card.counts.learn}</span>
            <span class="c-review" class:cur={card.queue === 2}>{card.counts.review}</span>
          </div>
        {/if}
        {#if plan && minutes}<span class="timer num">noch {left} min</span>{/if}
        {#if card.study.show_timer}<span class="timer num" class:capped={elapsed >= card.study.cap_secs}>{clock(elapsed)}</span>{/if}
      </div>
      <div class="tools">
        {#if card.study.seconds_question || card.study.seconds_answer}
          <button class="plain" class:active={autoAdvance} onclick={toggleAuto} title="Automatisch weiter (A)"><FastForward size={17} /></button>
        {/if}
        <button class="plain" onclick={undo} title="Rückgängig (⌘Z)"><Undo2 size={17} /></button>
        <button class="plain" onclick={() => (editing = true)} title="Bearbeiten (E)"><Pencil size={17} /></button>
      </div>
    {/if}
  </header>

  {#if done}
    <div class="done">
      {#if plan}
        <h1>{timeUp ? 'Lernplan geschafft.' : 'Alles erledigt.'}</h1>
        <p class="muted">{answered} {answered === 1 ? 'Karte' : 'Karten'} in {Math.max(1, Math.round((Date.now() - sessionStart) / 60000))} Minuten. {timeUp ? 'Was noch fällig ist, kannst du später oder morgen lernen.' : 'In keinem Stapel ist gerade noch etwas fällig.'}</p>
      {:else}
        <h1>{temporary ? 'Geschafft.' : 'Fertig für heute.'}</h1>
        <p class="muted">{temporary ? 'Die Karten sind neu eingeplant. Lernkarten, die noch offen sind, kehren in ihre Stapel zurück.' : `In „${deckName}“ ist gerade nichts mehr fällig. Lernkarten kommen nach ihrer Lernstufe zurück.`}</p>
      {/if}
      <div class="row">
        <button onclick={exit}>Zur Übersicht</button>
        <button class="ghost" onclick={undo}>Letzte Antwort rückgängig</button>
      </div>
    </div>
  {:else if card}
    <div class="card-area">
      <CardFrame html={revealed ? card.answer : card.question} css={card.css} ord={card.ord} onkey={onKey}
        autoplay={card.study.autoplay} hideAudio={prefs.hide_audio_play_buttons} />
    </div>
    <footer>
      {#if !revealed}
        <button class="reveal" onclick={reveal}>Antwort zeigen <kbd class="inv">Leertaste</kbd></button>
      {:else}
        <div class="answers">
          {#each BUTTONS as b, i}
            <button class="ans {b.cls}" onclick={() => answer(b.ease)}>
              {#if prefs.show_intervals_on_buttons}<span class="ivl num">{card.buttons[i]}</span>{/if}
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
      <Editor noteId={card.note_id} {flat} {notify} onSaved={async () => { editing = false; card = await fetchCard() }} onCancel={() => (editing = false)} />
    </div>
  </div>
{/if}

<style>
  .study { height: 100%; display: flex; flex-direction: column; }
  header { display: flex; align-items: center; padding: 14px 20px; gap: 16px; }
  .mid { margin: 0 auto; display: flex; align-items: center; gap: 20px; }
  .counts { display: flex; gap: 14px; font-weight: 650; font-size: 15px; }
  .timer { font-size: 14px; color: var(--ink-2); font-weight: 500; }
  .timer.capped { color: var(--m-red); }
  .tools .active { color: var(--paper); background: var(--ink); }
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
