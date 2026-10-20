<script>
  import { api } from './api.js'

  // Add mode without noteId, edit mode with it.
  let { noteId = null, flat, notify, onSaved, onCancel = null } = $props()

  let types = $state([])
  let typeId = $state(null)
  let deckId = $state(null)
  let fields = $state({})
  let tags = $state('')
  let saving = $state(false)
  let editors = $state([])

  const type = $derived(types.find((t) => t.id === typeId))

  const remember = (k, v) => { try { localStorage.setItem(k, String(v)) } catch {} }
  const recall = (k) => { try { return Number(localStorage.getItem(k)) || null } catch { return null } }

  async function load() {
    types = await api.note_types()
    if (noteId) {
      const n = await api.get_note(noteId)
      typeId = n.notetype_id
      deckId = n.deck_id
      fields = n.fields
      tags = n.tags.join(' ')
    } else {
      typeId = types.some((t) => t.id === recall('ba.type')) ? recall('ba.type') : (types.find((t) => t.basic) ?? types[0])?.id
      deckId = flat.some((d) => d.id === recall('ba.deck')) ? recall('ba.deck') : flat[0]?.id
      resetFields()
    }
  }

  function resetFields() {
    const t = types.find((t) => t.id === typeId)
    fields = Object.fromEntries((t?.fields ?? []).map((f) => [f, '']))
  }

  async function save() {
    if (saving) return
    const tagList = tags.split(/\s+/).filter(Boolean)
    saving = true
    try {
      if (noteId) {
        await api.update_note(noteId, $state.snapshot(fields), tagList, deckId)
        notify('Gespeichert')
      } else {
        await api.add_note(typeId, deckId, $state.snapshot(fields), tagList)
        remember('ba.type', typeId)
        remember('ba.deck', deckId)
        notify('Karte hinzugefügt')
        resetFields()
        editors[0]?.focus()
      }
      onSaved?.()
    } catch (e) {
      notify(String(e?.message ?? e), true)
    } finally {
      saving = false
    }
  }

  // Cmd/Ctrl+Shift+C wraps the selection in the next cloze number, like Anki.
  function cloze() {
    const used = [...Object.values(fields).join('').matchAll(/\{\{c(\d+)::/g)].map((m) => Number(m[1]))
    const n = (used.length ? Math.max(...used) : 0) + 1
    const text = getSelection()?.toString() ?? ''
    document.execCommand('insertText', false, `{{c${n}::${text}}}`)
  }

  function onKey(e) {
    const mod = e.metaKey || e.ctrlKey
    if (mod && e.key === 'Enter') return e.preventDefault(), save()
    if (mod && e.shiftKey && e.key.toLowerCase() === 'c') return e.preventDefault(), cloze()
    if (e.key === 'Escape' && onCancel) onCancel()
  }

  load()
</script>

<form class="editor" onsubmit={(e) => { e.preventDefault(); save() }}>
  <div class="meta">
    <label>Notiztyp
      <select bind:value={typeId} onchange={resetFields} disabled={!!noteId}>
        {#each types as t}<option value={t.id}>{t.name}</option>{/each}
      </select>
    </label>
    <label>Stapel
      <select bind:value={deckId}>
        {#each flat as d}<option value={d.id}>{d.name}</option>{/each}
      </select>
    </label>
  </div>

  {#each Object.keys(fields) as name, i (name)}
    <div class="field">
      <span class="fname">{name}</span>
      <div class="rich" contenteditable="true" role="textbox" aria-multiline="true" aria-label={name} tabindex="0"
        bind:this={editors[i]} bind:innerHTML={fields[name]} onkeydown={onKey}></div>
    </div>
  {/each}

  <label class="field">
    <span class="fname">Tags</span>
    <input bind:value={tags} placeholder="durch Leerzeichen getrennt" onkeydown={onKey} />
  </label>

  <div class="bar">
    {#if type?.cloze}<span class="muted hint">Lückentext: Text markieren, <kbd>⌘⇧C</kbd></span>{/if}
    {#if onCancel}<button type="button" class="ghost" onclick={onCancel}>Abbrechen</button>{/if}
    <button type="submit" disabled={saving || !flat.length}>{noteId ? 'Speichern' : 'Hinzufügen'} <kbd class="inv">⌘↵</kbd></button>
  </div>
  {#if !flat.length}<p class="muted">Lege zuerst einen Stapel an.</p>{/if}
</form>

<style>
  .editor { display: flex; flex-direction: column; gap: 16px; }
  .meta { display: flex; gap: 12px; flex-wrap: wrap; }
  label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--ink-2); min-width: 0; }
  .meta label { flex: 1 1 180px; }
  select { width: 100%; }
  .field { display: flex; flex-direction: column; gap: 6px; }
  .fname { font-size: 13px; color: var(--ink-2); font-weight: 500; }
  .rich {
    min-height: 64px; padding: 10px 12px; border: 1px solid var(--rule-2); border-radius: var(--radius);
    font-size: 16px; line-height: 1.5; background: var(--paper); outline: none; overflow-wrap: anywhere;
  }
  .rich:focus { border-color: var(--ink); }
  .rich :global(img) { max-width: 100%; }
  .bar { display: flex; justify-content: flex-end; align-items: center; gap: 8px; }
  .hint { margin-right: auto; font-size: 13px; }
  kbd.inv { color: var(--paper); border-color: color-mix(in srgb, var(--paper) 40%, transparent); }
</style>
