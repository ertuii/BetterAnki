<script>
  import { Copy } from '@lucide/svelte'
  import { api } from './api.js'

  let { notify, refresh } = $props()

  let account = $state(null)
  let user = $state('')
  let pass = $state('')
  let syncing = $state(false)
  let full = $state(null) // {direction, message} when AnkiWeb needs a one-way sync
  let backups = $state([])
  let backingUp = $state(false)
  let confirmRestore = $state(null)
  let folder = $state('')
  let mcp = $state('')

  async function load() {
    ;[account, backups, folder, mcp] = await Promise.all([api.sync_account(), api.backups(), api.data_folder(), api.mcp_command()])
  }

  const fail = (e) => notify(String(e?.message ?? e), true)

  async function login() {
    try {
      await api.sync_login(user, pass)
      pass = ''
      notify('Bei AnkiWeb angemeldet')
      await load()
    } catch (e) {
      fail(e)
    }
  }

  async function sync() {
    syncing = true
    full = null
    try {
      const r = await api.sync()
      if (r.full_required) full = r
      else notify(r.message || 'Synchronisiert')
      await refresh()
    } catch (e) {
      fail(e)
    } finally {
      syncing = false
    }
  }

  async function fullSync(upload) {
    syncing = true
    try {
      await api.full_sync(upload)
      full = null
      notify(upload ? 'Zu AnkiWeb hochgeladen' : 'Von AnkiWeb heruntergeladen')
      await refresh()
    } catch (e) {
      fail(e)
    } finally {
      syncing = false
    }
  }

  async function logout() {
    await api.sync_logout()
    full = null
    await load()
  }

  async function backupNow() {
    backingUp = true
    try {
      await api.backup(true)
      notify('Sicherung erstellt')
      await load()
    } catch (e) {
      fail(e)
    } finally {
      backingUp = false
    }
  }

  async function restore(b) {
    if (confirmRestore !== b.path) return (confirmRestore = b.path)
    confirmRestore = null
    try {
      await api.restore_backup(b.path)
      notify('Sicherung wiederhergestellt')
      await Promise.all([load(), refresh()])
    } catch (e) {
      fail(e)
    }
  }

  async function exportAll() {
    const path = await api.pick_export_file('BetterAnki-Sammlung', 'colpkg')
    if (!path) return
    try {
      await api.export_collection(path, true)
      notify('Sammlung exportiert')
    } catch (e) {
      fail(e)
    }
  }

  async function copy(text) {
    try {
      await navigator.clipboard.writeText(text)
      notify('Kopiert')
    } catch {
      notify('Kopieren nicht möglich – bitte markieren und kopieren', true)
    }
  }

  const when = (t) => new Date(t * 1000).toLocaleString('de-DE', { dateStyle: 'medium', timeStyle: 'short' })
  const claudeCode = $derived(`claude mcp add betteranki -- ${mcp}`)

  load()
</script>

<div class="settings">
  <h1>Einstellungen</h1>

  <section>
    <h2>AnkiWeb-Synchronisierung</h2>
    <p class="muted">Optional. Hält diese Sammlung mit AnkiWeb und der Anki-App auf dem Handy abgeglichen. Ohne Anmeldung bleibt alles nur auf diesem Laptop.</p>
    {#if account}
      <div class="row">
        <span>Angemeldet als <b>{account}</b></span>
        <button disabled={syncing} onclick={sync}>{syncing ? 'Synchronisiere …' : 'Jetzt synchronisieren'}</button>
        <button class="ghost" onclick={logout}>Abmelden</button>
      </div>
      {#if full}
        <div class="choice" role="alert">
          <b>Einmalige Komplettsynchronisierung nötig.</b>
          <p>{full.message || 'Die Sammlungen auf AnkiWeb und hier lassen sich nicht zusammenführen. Wähle, welche Seite gilt; die andere wird ersetzt.'}</p>
          <div class="row">
            <button class={full.direction === 'download' ? '' : 'ghost'} disabled={syncing} onclick={() => fullSync(false)}>Von AnkiWeb laden (ersetzt diese Sammlung)</button>
            <button class={full.direction === 'upload' ? '' : 'ghost'} disabled={syncing} onclick={() => fullSync(true)}>Hochladen (ersetzt AnkiWeb)</button>
          </div>
        </div>
      {/if}
    {:else}
      <form class="login" onsubmit={(e) => { e.preventDefault(); login() }}>
        <input type="email" bind:value={user} placeholder="E-Mail" autocomplete="username" aria-label="AnkiWeb-E-Mail" />
        <input type="password" bind:value={pass} placeholder="Passwort" autocomplete="current-password" aria-label="AnkiWeb-Passwort" />
        <button type="submit" disabled={!user || !pass}>Anmelden</button>
      </form>
      <p class="muted small">Das Passwort wird nicht gespeichert, nur ein Anmeldeschlüssel von AnkiWeb.</p>
    {/if}
  </section>

  <section>
    <h2>Sicherungen</h2>
    <p class="muted">Beim Beenden sichert BetterAnki automatisch (höchstens alle 30 Minuten). Vor jedem Wiederherstellen wird der aktuelle Stand zusätzlich gesichert.</p>
    <div class="row">
      <button class="ghost" disabled={backingUp} onclick={backupNow}>{backingUp ? 'Sichere …' : 'Jetzt sichern'}</button>
      <button class="ghost" onclick={exportAll}>Ganze Sammlung exportieren (.colpkg)</button>
    </div>
    {#if backups.length}
      <table>
        <thead><tr><th>Sicherung</th><th>Größe</th><th></th></tr></thead>
        <tbody>
          {#each backups as b (b.path)}
            <tr>
              <td>{when(b.mtime)}</td>
              <td class="num muted">{b.size_kb < 1024 ? `${b.size_kb} KB` : `${(b.size_kb / 1024).toFixed(1)} MB`}</td>
              <td class="w"><button class="ghost sm" onclick={() => restore(b)} onblur={() => (confirmRestore = null)}>{confirmRestore === b.path ? 'Aktuellen Stand ersetzen?' : 'Wiederherstellen'}</button></td>
            </tr>
          {/each}
        </tbody>
      </table>
    {:else}
      <p class="muted small">Noch keine Sicherungen.</p>
    {/if}
  </section>

  <section>
    <h2>Claude verbinden</h2>
    <p class="muted">Damit Claude Karten anlegen, suchen und bearbeiten kann. In Claude Code im Terminal ausführen:</p>
    <div class="cmd"><code>{claudeCode}</code><button class="plain sm" aria-label="Befehl kopieren" onclick={() => copy(claudeCode)}><Copy size={16} /></button></div>
    <p class="muted small">Für Claude Desktop: als MCP-Server mit diesem Befehl eintragen: <code>{mcp}</code></p>
  </section>

  <section>
    <h2>Daten</h2>
    <p class="muted">Deine Sammlung liegt nur auf diesem Rechner:</p>
    <div class="cmd"><code>{folder}</code><button class="plain sm" aria-label="Pfad kopieren" onclick={() => copy(folder)}><Copy size={16} /></button></div>
  </section>
</div>

<style>
  .settings { padding: 32px 40px 56px; max-width: 820px; display: flex; flex-direction: column; gap: 28px; }
  h1 { font-size: 26px; font-weight: 750; letter-spacing: -0.02em; }
  section { display: flex; flex-direction: column; gap: 12px; padding-top: 20px; border-top: 1px solid var(--rule); }
  h2 { font-size: 16px; font-weight: 700; }
  section > p { font-size: 14px; max-width: 65ch; }
  .small { font-size: 13px !important; }
  .row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .row span { margin-right: 8px; }
  .login { display: flex; gap: 8px; flex-wrap: wrap; }
  .login input { flex: 1 1 200px; }
  .choice { background: var(--warn-bg); color: var(--warn-ink); border-radius: 10px; padding: 14px 16px; display: flex; flex-direction: column; gap: 8px; }
  .choice p { font-size: 14px; }
  .cmd { display: flex; align-items: center; gap: 8px; background: var(--paper-2); border-radius: var(--radius); padding: 8px 8px 8px 12px; }
  .cmd code { flex: 1; font: 13px/1.5 ui-monospace, 'SF Mono', Menlo, Consolas, monospace; overflow-wrap: anywhere; }
  p code { font: 12px ui-monospace, 'SF Mono', Menlo, Consolas, monospace; background: var(--paper-2); padding: 1px 5px; border-radius: 4px; overflow-wrap: anywhere; }
  .w { width: 1%; white-space: nowrap; }
</style>
