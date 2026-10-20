<script>
  import { ArrowLeft } from '@lucide/svelte'
  import { api } from './api.js'

  let { deckId, notify, onBack } = $props()

  let o = $state(null)
  let learnSteps = $state('')
  let relearnSteps = $state('')
  let saving = $state(false)
  let optimizing = $state(false)
  let newPreset = $state(null)

  // Anki stores steps in minutes; show them as "1m 10m 1d".
  const fmtSteps = (xs) => xs.map((m) => (m >= 1440 && m % 1440 === 0 ? `${m / 1440}d` : m >= 60 && m % 60 === 0 ? `${m / 60}h` : `${m}m`)).join(' ')
  function parseSteps(text) {
    return text.split(/[\s,]+/).filter(Boolean).map((t) => {
      const m = t.match(/^(\d+(?:[.,]\d+)?)\s*([smhd]?)$/i)
      if (!m) throw new Error(`„${t}“ ist kein Schritt. Beispiele: 10m, 1h, 1d`)
      const n = Number(m[1].replace(',', '.'))
      return { s: n / 60, m: n, h: n * 60, d: n * 1440 }[(m[2] || 'm').toLowerCase()]
    })
  }

  async function load(presetId) {
    o = await api.deck_options(deckId, presetId ?? null)
    learnSteps = fmtSteps(o.learn_steps)
    relearnSteps = fmtSteps(o.relearn_steps)
  }

  async function save() {
    saving = true
    try {
      const data = { ...$state.snapshot(o), learn_steps: parseSteps(learnSteps), relearn_steps: parseSteps(relearnSteps) }
      await api.save_deck_options(deckId, data)
      notify('Optionen gespeichert')
      await load()
    } catch (e) {
      notify(String(e?.message ?? e), true)
    } finally {
      saving = false
    }
  }

  async function createPreset() {
    if (!newPreset?.trim()) return (newPreset = null)
    try {
      await api.new_preset(deckId, newPreset)
      notify(`Voreinstellung „${newPreset}“ angelegt`)
      newPreset = null
      await load()
    } catch (e) {
      notify(String(e?.message ?? e), true)
    }
  }

  async function optimize() {
    optimizing = true
    try {
      const r = await api.optimize_fsrs(deckId)
      notify(r.changed ? `FSRS an ${r.reviews} Wiederholungen angepasst` : r.reviews < 400
        ? `Erst ${r.reviews} Wiederholungen – FSRS nutzt bis dahin Standardwerte`
        : 'Parameter sind bereits optimal')
      await load()
    } catch (e) {
      notify(String(e?.message ?? e), true)
    } finally {
      optimizing = false
    }
  }

  load()
</script>

<div class="opts">
  <header>
    <button class="plain" onclick={onBack}><ArrowLeft size={17} />Zurück</button>
  </header>
  {#if o}
    <h1>Optionen für „{o.deck_name}“</h1>

    <section>
      <h2>Voreinstellung</h2>
      <p class="muted">Optionen gehören zu einer Voreinstellung, die mehrere Stapel teilen können.</p>
      <div class="row">
        <select bind:value={o.preset_id} onchange={() => load(o.preset_id)}>
          {#each o.presets as p}<option value={p.id}>{p.name} · {p.decks} Stapel</option>{/each}
        </select>
        {#if newPreset === null}
          <button class="ghost" onclick={() => (newPreset = '')}>Neue Voreinstellung</button>
        {:else}
          <!-- svelte-ignore a11y_autofocus -->
          <input bind:value={newPreset} placeholder="Name" autofocus onkeydown={(e) => e.key === 'Enter' ? createPreset() : e.key === 'Escape' && (newPreset = null)} />
          <button class="ghost" onclick={createPreset}>Anlegen</button>
        {/if}
      </div>
    </section>

    <section>
      <h2>Tageslimits</h2>
      <div class="fields">
        <label>Neue Karten pro Tag<input type="number" min="0" bind:value={o.new_per_day} /></label>
        <label>Wiederholungen pro Tag<input type="number" min="0" bind:value={o.reviews_per_day} /></label>
      </div>
    </section>

    <section>
      <h2>Neue Karten</h2>
      <div class="fields">
        <label>Lernschritte<input bind:value={learnSteps} placeholder="1m 10m" /><small>z. B. 1m 10m 1d</small></label>
        <label>Abschlussintervall (Tage)<input type="number" min="1" bind:value={o.graduating_interval_good} /></label>
        <label>Intervall bei „Einfach“ (Tage)<input type="number" min="1" bind:value={o.graduating_interval_easy} /></label>
      </div>
    </section>

    <section>
      <h2>Vergessene Karten</h2>
      <div class="fields">
        <label>Neulernschritte<input bind:value={relearnSteps} placeholder="10m" /></label>
        <label>Lästling ab Fehlversuchen<input type="number" min="1" bind:value={o.leech_threshold} /></label>
        <label>Bei Lästlingen
          <select bind:value={o.leech_action}>
            <option value={1}>Nur markieren</option>
            <option value={0}>Aussetzen</option>
          </select>
        </label>
      </div>
    </section>

    <section>
      <h2>Zurückstellen</h2>
      <p class="muted">Verwandte Karten derselben Notiz erst am nächsten Tag zeigen.</p>
      <div class="checks">
        <label class="check"><input type="checkbox" bind:checked={o.bury_new} />Neue verwandte Karten</label>
        <label class="check"><input type="checkbox" bind:checked={o.bury_reviews} />Verwandte Wiederholungen</label>
        <label class="check"><input type="checkbox" bind:checked={o.bury_interday_learning} />Verwandte Lernkarten (über Tage)</label>
      </div>
    </section>

    <section>
      <h2>Planung</h2>
      <label class="check"><input type="checkbox" bind:checked={o.fsrs} />FSRS verwenden <span class="muted">(gilt für alle Stapel)</span></label>
      <p class="muted">FSRS plant Wiederholungen aus deinem Lernverlauf statt mit festen Faktoren und braucht meist weniger Wiederholungen für dieselbe Erinnerung.</p>
      {#if o.fsrs}
        <div class="fields">
          <label>Gewünschte Erinnerung
            <span class="range"><input type="range" min="0.7" max="0.97" step="0.01" bind:value={o.desired_retention} /><b class="num">{Math.round(o.desired_retention * 100)} %</b></span>
            <small>Höher = sicherer, aber mehr Wiederholungen pro Tag.</small>
          </label>
          <div class="opt">
            <span class="lbl">Parameter</span>
            <button class="ghost" disabled={optimizing} onclick={optimize}>{optimizing ? 'Optimiere …' : 'An meinen Verlauf anpassen'}</button>
            <small>{o.fsrs_optimized ? 'Angepasst an deinen Verlauf.' : 'Noch Standardwerte.'}</small>
          </div>
        </div>
      {/if}
      <div class="fields">
        <label>Maximales Intervall (Tage)<input type="number" min="1" bind:value={o.maximum_review_interval} /></label>
      </div>
    </section>

    <div class="bar">
      <button class="ghost" onclick={onBack}>Abbrechen</button>
      <button disabled={saving} onclick={save}>{saving ? 'Speichere …' : 'Speichern'}</button>
    </div>
  {/if}
</div>

<style>
  .opts { padding: 20px 40px 56px; max-width: 820px; display: flex; flex-direction: column; gap: 28px; }
  header { margin-left: -8px; }
  h1 { font-size: 26px; font-weight: 750; letter-spacing: -0.02em; }
  section { display: flex; flex-direction: column; gap: 10px; padding-top: 20px; border-top: 1px solid var(--rule); }
  h2 { font-size: 16px; font-weight: 700; }
  section > p { font-size: 13px; max-width: 65ch; }
  .row { display: flex; gap: 8px; }
  .row select { width: 280px; }
  .fields { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
  label, .opt { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--ink-2); }
  .lbl { font-size: 13px; }
  small { font-size: 12px; color: var(--ink-3); }
  .checks { display: flex; flex-direction: column; gap: 8px; }
  label.check { flex-direction: row; align-items: center; gap: 10px; font-size: 14px; color: var(--ink); }
  .range { display: flex; align-items: center; gap: 12px; }
  .range input { flex: 1; accent-color: var(--ink); height: auto; border: 0; padding: 0; }
  .range b { color: var(--ink); width: 44px; }
  .bar { display: flex; justify-content: flex-end; gap: 8px; position: sticky; bottom: 0; padding: 16px 0; background: var(--paper); border-top: 1px solid var(--rule); }
</style>
