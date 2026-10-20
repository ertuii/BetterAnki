<script>
  import { api } from './api.js'

  // Finds Anki desktop profiles on this computer and copies or merges one into Muisti.
  let { notify, onDone, hasCards = false, compact = false } = $props()

  let profiles = $state(null)
  let busy = $state(null)
  let confirmReplace = $state(null)

  async function load() {
    profiles = await api.anki_profiles()
  }

  async function migrate(p, mode) {
    if (mode === 'replace' && hasCards && confirmReplace !== p.path) return (confirmReplace = p.path)
    confirmReplace = null
    busy = p.path
    try {
      notify(await api.migrate_from_anki(p.path, mode))
      await load()
      onDone?.()
    } catch (e) {
      notify(String(e?.message ?? e), true)
    } finally {
      busy = null
    }
  }

  const when = (t) => new Date(t * 1000).toLocaleDateString('de-DE', { dateStyle: 'medium' })

  load()
</script>

{#if profiles?.length}
  <ul class="profiles" class:compact>
    {#each profiles as p (p.path)}
      <li>
        <div>
          <b>{p.name}</b>
          <span class="muted num">{p.locked ? 'Anki ist geöffnet' : `${p.cards} Karten · ${p.notes} Notizen · ${p.media} Medien`} · zuletzt {when(p.modified)}</span>
        </div>
        <div class="actions">
          {#if p.locked}
            <button class="ghost sm" onclick={load}>Anki geschlossen? Neu prüfen</button>
          {:else if hasCards}
            <button class="sm" disabled={!!busy} onclick={() => migrate(p, 'merge')}>{busy === p.path ? 'Übernehme …' : 'Hinzufügen'}</button>
            <button class="ghost sm" disabled={!!busy} onclick={() => migrate(p, 'replace')} onblur={() => (confirmReplace = null)}>
              {confirmReplace === p.path ? 'Meine Karten ersetzen?' : 'Ersetzen'}
            </button>
          {:else}
            <button class="sm" disabled={!!busy} onclick={() => migrate(p, 'replace')}>{busy === p.path ? 'Übernehme …' : 'Übernehmen'}</button>
          {/if}
        </div>
      </li>
    {/each}
  </ul>
  {#if !compact}
    <p class="muted small">
      {hasCards ? '„Hinzufügen“ führt die Anki-Karten mit deinen zusammen, „Ersetzen“ übernimmt die Anki-Sammlung 1:1 (dein Stand landet in den Sicherungen).' : 'Übernimmt Stapel, Karten, Lernverlauf, Notiztypen, Optionen und Medien.'}
      Anki selbst bleibt unverändert.
    </p>
  {/if}
{:else if profiles && !compact}
  <p class="muted small">Keine Anki-Installation gefunden. Exportiere in Anki über <i>Datei → Exportieren</i> eine <b>.colpkg</b>-Datei und ziehe sie hier ins Fenster.</p>
{/if}

<style>
  .profiles { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; }
  .profiles li { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 10px 0; border-bottom: 1px solid var(--rule); }
  .profiles li:last-child { border-bottom: 0; }
  .profiles.compact li { padding: 6px 0; border: 0; }
  .profiles b { margin-right: 10px; }
  .profiles span { font-size: 13px; }
  .actions { display: flex; gap: 8px; flex: none; }
  .small { font-size: 13px; }
</style>
