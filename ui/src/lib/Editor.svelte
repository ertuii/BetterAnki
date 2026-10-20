<script>
  import DOMPurify from 'dompurify'
  import { api } from './api.js'

  // Note HTML (imported decks, cards from Claude) runs in the app window here, unlike CardFrame's sandbox:
  // everything that reaches a field is sanitized, or it could call window.pywebview.api.
  const clean = (html) => DOMPurify.sanitize(html)

  // Add mode without noteId, edit mode with it.
  let { noteId = null, flat, notify, onSaved, onCancel = null } = $props()

  let types = $state([])
  let typeId = $state(null)
  let deckId = $state(null)
  let fields = $state({})
  let stored = {} // edit mode: field values as saved, and as shown after sanitizing
  let shown = {}
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
      stored = n.fields
      shown = Object.fromEntries(Object.entries(n.fields).map(([k, v]) => [k, clean(v)]))
      fields = { ...shown }
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
        // fields left untouched keep their stored HTML; only edited ones are saved in sanitized form
        const out = Object.fromEntries(Object.entries($state.snapshot(fields)).map(([k, v]) => [k, v === shown[k] ? stored[k] : v]))
        await api.update_note(noteId, out, tagList, deckId)
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

  let pasteStrips = false
  api.preferences().then((p) => (pasteStrips = p.editing.paste_strips_formatting))

  // Images (pasted or dropped) go into the collection's media folder like in Anki.
  async function insertFiles(files) {
    for (const f of files) {
      if (!f.type.startsWith('image/') && !f.type.startsWith('audio/')) continue
      const b64 = await new Promise((res) => {
        const r = new FileReader()
        r.onload = () => res(String(r.result).split(',')[1])
        r.readAsDataURL(f)
      })
      const name = await api.add_media(f.name || `bild-${Date.now()}.png`, b64)
      const html = f.type.startsWith('image/') ? `<img src="${name}">` : `[sound:${name}]`
      document.execCommand('insertHTML', false, clean(html)) // the file name is untrusted
    }
  }

  function onPaste(e) {
    const files = [...(e.clipboardData?.files ?? [])]
    if (files.length) {
      e.preventDefault()
      insertFiles(files)
    } else if (pasteStrips) {
      e.preventDefault()
      document.execCommand('insertText', false, e.clipboardData.getData('text/plain'))
    } else if (e.clipboardData?.types.includes('text/html')) {
      e.preventDefault()
      document.execCommand('insertHTML', false, clean(e.clipboardData.getData('text/html')))
    }
  }

  function onDrop(e) {
    const files = [...(e.dataTransfer?.files ?? [])]
    if (!files.length && e.dataTransfer?.types.includes('text/html')) {
      e.preventDefault()
      e.stopPropagation()
      const at = document.caretRangeFromPoint?.(e.clientX, e.clientY) // insert where it was dropped
      if (at) getSelection().removeAllRanges(), getSelection().addRange(at)
      return document.execCommand('insertHTML', false, clean(e.dataTransfer.getData('text/html')))
    }
    if (!files.length) return
    e.preventDefault()
    e.stopPropagation() // not an import: keep it away from the window-level drop handler
    insertFiles(files)
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
        bind:this={editors[i]} bind:innerHTML={fields[name]} onkeydown={onKey} onpaste={onPaste} ondrop={onDrop}></div>
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
