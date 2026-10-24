<script>
  import { Copy } from '@lucide/svelte'
  import { api, web } from './api.js'
  import AnkiMigration from './AnkiMigration.svelte'
  import { applyTheme } from './theme.js'

  let { notify, refresh, checkUpdate } = $props()

  let cloud = $state(null) // e-mail of the Muisti account
  let cEmail = $state('')
  let cPass = $state('')
  let cSyncing = $state(false)
  let newPass = $state('')
  let account = $state(null)
  let user = $state('')
  let pass = $state('')
  let syncing = $state(false)
  let full = $state(null) // {direction, message} when AnkiWeb needs a one-way sync
  let backups = $state([])
  let backingUp = $state(false)
  let confirmRestore = $state(null)
  let storage = $state(null)
  let moveTarget = $state(null) // {folder, has_collection, synced_folder}
  let moving = $state(false)
  let claude = $state(null)
  let connecting = $state(null)
  let prefs = $state(null)
  let cardCount = $state(0)
  let prefTimer
  let features = $state(null)
  let version = $state('')
  let theme = $state('system')
  api.theme().then((t) => (theme = t))
  const THEMES = [{ v: 'system', label: 'Wie System' }, { v: 'light', label: 'Hell' }, { v: 'dark', label: 'Dunkel' }]

  async function setTheme(t) {
    theme = t
    applyTheme(t)
    try {
      await api.set_theme(t)
    } catch (e) {
      fail(e)
    }
  }

  async function saveFeatures() {
    try {
      await api.save_features($state.snapshot(features))
      await refresh()
      notify('Gespeichert')
    } catch (e) {
      fail(e)
    }
  }
  let checking = $state(false)

  async function lookForUpdate() {
    checking = true
    try {
      const u = await checkUpdate(true)
      notify(u ? `Version ${u.version} ist verfügbar. Klicke links auf „Aktualisieren“.` : 'Du hast die neueste Version.')
    } catch (e) {
      fail(e)
    } finally {
      checking = false
    }
  }

  async function load() {
    cloud = await api.cloud_account()
    ;[account, backups, storage, claude, prefs, cardCount] = await Promise.all([
      api.sync_account(), api.backups(), api.storage(), api.claude_status(), api.preferences(), api.stats().then((s) => s.cards),
    ])
  }

  // Preferences save themselves shortly after each change.
  function savePrefs() {
    clearTimeout(prefTimer)
    prefTimer = setTimeout(async () => {
      try {
        await api.save_preferences($state.snapshot(prefs))
        notify('Einstellung gespeichert')
      } catch (e) {
        fail(e)
      }
    }, 400)
  }

  async function chooseFolder() {
    try {
      const folder = await api.pick_folder()
      if (!folder) return
      const check = await api.check_storage_target(folder)
      if (check.same) return notify('Das ist bereits der Speicherort.')
      moveTarget = { folder, ...check }
    } catch (e) {
      fail(e)
    }
  }

  async function applyStorage(mode, folder = moveTarget.folder) {
    moving = true
    try {
      notify(await api.change_storage(folder, mode))
      moveTarget = null
      await Promise.all([load(), refresh()])
    } catch (e) {
      fail(e)
    } finally {
      moving = false
    }
  }

  async function connect(target) {
    connecting = target
    try {
      notify(await api.connect_claude(target))
      claude = await api.claude_status()
    } catch (e) {
      fail(e)
    } finally {
      connecting = null
    }
  }

  async function disconnect(target) {
    try {
      await api.disconnect_claude(target)
      claude = await api.claude_status()
    } catch (e) {
      fail(e)
    }
  }

  const fail = (e) => notify(String(e?.message ?? e), true)

  async function cloudLogin(register) {
    try {
      if (register && !(await api.cloud_register(cEmail, cPass))) {
        notify('Fast fertig: Bestätige deine E-Mail über den Link im Postfach und melde dich dann hier an.')
        return
      }
      if (!register) await api.cloud_login(cEmail, cPass)
      cPass = ''
      await load()
      await cloudSync()
    } catch (e) {
      fail(e)
    }
  }

  async function cloudSync() {
    cSyncing = true
    try {
      const r = await api.cloud_sync()
      notify(r.sent || r.received || r.media ? `Synchronisiert: ${r.sent} gesendet, ${r.received} empfangen` : 'Alles aktuell')
      await refresh()
    } catch (e) {
      fail(e)
    } finally {
      cSyncing = false
    }
  }

  async function changePassword() {
    try {
      await api.change_password(newPass)
      newPass = ''
      notify('Passwort geändert')
    } catch (e) {
      fail(e)
    }
  }

  async function cloudLogout() {
    await api.cloud_logout()
    await load()
  }

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
    const path = await api.pick_export_file('Muisti-Sammlung', 'colpkg')
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
  const CLIENTS = [
    { key: 'desktop', name: 'Claude Desktop', hint: 'Die Claude-App für Mac und Windows. Danach Claude Desktop einmal neu starten.' },
    { key: 'code', name: 'Claude Code', hint: 'Claude im Terminal oder in der IDE. Gilt für alle neuen Sitzungen.' },
  ]

  load()
  api.app_version().then((v) => (version = v))
  api.features().then((f) => (features = f))

  const EXTRAS = [
    { key: 'exams', name: 'Prüfungstermine', hint: 'Eigene Seite „Prüfungen“: Klausurdatum pro Stapel eintragen. Die App rechnet aus, wie viele neue Karten pro Tag nötig sind, und markiert die Prüfung im Zeitstrahl.' },
    { key: 'plan', name: 'Lernplan', hint: 'Auf der Heute-Seite eine Dauer wählen und über alle Stapel lernen, Stapel mit naher Prüfung zuerst.' },
    { key: 'weak', name: 'Schwachstellen', hint: 'In der Statistik sehen, bei welchen Themen und Stapeln du am meisten vergisst, und gezielt üben.' },
  ]
</script>

<div class="settings">
  <h1>Einstellungen</h1>

  <section>
    <h2>Darstellung</h2>
    <div class="seg" role="radiogroup" aria-label="Farbschema">
      {#each THEMES as t}
        <button role="radio" aria-checked={theme === t.v} class:on={theme === t.v} onclick={() => setTheme(t.v)}>{t.label}</button>
      {/each}
    </div>
  </section>

  {#if features}
    <section>
      <h2>Zusatzfunktionen</h2>
      <p class="muted">Funktionen, die es in Anki nicht gibt. Schalte nur ein, was du brauchst.</p>
      <div class="extras">
        {#each EXTRAS as x}
          <label class="extra"><input type="checkbox" bind:checked={features[x.key]} onchange={saveFeatures} />
            <span><b>{x.name}</b><small class="muted">{x.hint}</small></span>
          </label>
        {/each}
        <label class="extra"><input type="checkbox" bind:checked={features.inbox} onchange={saveFeatures} />
          <span><b>Karten von Claude erst prüfen</b><small class="muted">Neue Karten von Claude warten im Eingang, bis du sie übernimmst. Ausgeschaltet werden sie sofort gelernt.</small></span>
        </label>
      </div>
    </section>
  {/if}

  {#if !web}
  <section>
    <h2>Von Anki übernehmen</h2>
    <p class="muted">Bringt deine Anki-Sammlung mit Lernstand in Muisti. Anki vorher schließen.</p>
    <AnkiMigration {notify} hasCards={cardCount > 0} onDone={async () => { await refresh(); await load() }} />
  </section>
  {/if}

  {#if prefs}
    <section oninput={savePrefs} onchange={savePrefs}>
      <h2>Lernen</h2>
      <div class="fields">
        <label>Neuer Tag beginnt um
          <select bind:value={prefs.scheduling.rollover}>{#each Array(24) as _, h}<option value={h}>{h}:00 Uhr</option>{/each}</select>
        </label>
        <label>Vorauslernen bis (Minuten)
          <input type="number" min="0" value={Math.round(prefs.scheduling.learn_ahead_secs / 60)}
            oninput={(e) => (prefs.scheduling.learn_ahead_secs = Number(e.currentTarget.value) * 60)} />
          <small>Lernkarten, die bald fällig werden, schon vorher zeigen.</small>
        </label>
        <label>Zeitlimit pro Sitzung (Minuten, 0 = aus)
          <input type="number" min="0" value={Math.round(prefs.reviewing.time_limit_secs / 60)}
            oninput={(e) => (prefs.reviewing.time_limit_secs = Number(e.currentTarget.value) * 60)} />
        </label>
      </div>
      <div class="checks">
        <label class="check"><input type="checkbox" bind:checked={prefs.scheduling.day_learn_first} />Lernkarten (über Tage) vor Wiederholungen zeigen</label>
        <label class="check"><input type="checkbox" bind:checked={prefs.reviewing.show_remaining_due_counts} />Verbleibende Karten beim Lernen anzeigen</label>
        <label class="check"><input type="checkbox" bind:checked={prefs.reviewing.show_intervals_on_buttons} />Nächstes Intervall über den Antworttasten anzeigen</label>
        <label class="check"><input type="checkbox" bind:checked={prefs.reviewing.hide_audio_play_buttons} />Wiedergabeknöpfe auf Karten ausblenden</label>
        <label class="check"><input type="checkbox" bind:checked={prefs.reviewing.load_balancer_enabled} />Wiederholungen gleichmäßig auf Tage verteilen (Lastverteilung)</label>
        <label class="check"><input type="checkbox" bind:checked={prefs.reviewing.fsrs_short_term_with_steps_enabled} />FSRS auch für Lernschritte am selben Tag nutzen</label>
      </div>
    </section>

    <section oninput={savePrefs} onchange={savePrefs}>
      <h2>Editor und Suche</h2>
      <div class="fields">
        <label>Standardsuche im Browser<input bind:value={prefs.editing.default_search_text} placeholder="z. B. is:due" /></label>
      </div>
      <div class="checks">
        <label class="check"><input type="checkbox" bind:checked={prefs.editing.adding_defaults_to_current_deck} />Beim Hinzufügen den zuletzt benutzten Stapel vorschlagen</label>
        <label class="check"><input type="checkbox" bind:checked={prefs.editing.paste_strips_formatting} />Formatierung beim Einfügen entfernen</label>
        <label class="check"><input type="checkbox" bind:checked={prefs.editing.ignore_accents_in_search} />Akzente bei der Suche ignorieren (é = e)</label>
      </div>
    </section>
  {/if}

  <section>
    <h2>Muisti-Konto</h2>
    {#if web}
      <p class="muted">Änderungen gehen sofort online. Was du in der Desktop-App lernst, erscheint hier, sobald sie synchronisiert hat.</p>
    {:else}
      <p class="muted">Lernen im Browser und auf mehreren Rechnern: Mit Konto gleicht Muisti deine Karten beim Start, alle paar Minuten und beim Beenden ab.</p>
    {/if}
    {#if cloud}
      <div class="row">
        <span>Angemeldet als <b>{cloud}</b></span>
        <button disabled={cSyncing} onclick={cloudSync}>{cSyncing ? 'Synchronisiere …' : 'Jetzt synchronisieren'}</button>
        <button class="ghost" onclick={cloudLogout}>Abmelden</button>
      </div>
      {#if web}
        <form class="login" onsubmit={(e) => { e.preventDefault(); changePassword() }}>
          <input type="password" bind:value={newPass} placeholder="Neues Passwort" autocomplete="new-password" aria-label="Neues Passwort" />
          <button type="submit" class="ghost" disabled={newPass.length < 8}>Passwort ändern</button>
        </form>
      {/if}
    {:else if account}
      <p class="muted small">Du bist bei AnkiWeb angemeldet. Melde dich dort ab, um stattdessen ein Muisti-Konto zu nutzen.</p>
    {:else}
      <form class="login" onsubmit={(e) => { e.preventDefault(); cloudLogin(false) }}>
        <input type="email" bind:value={cEmail} placeholder="E-Mail" autocomplete="username" aria-label="E-Mail fürs Muisti-Konto" />
        <input type="password" bind:value={cPass} placeholder="Passwort" autocomplete="current-password" aria-label="Passwort fürs Muisti-Konto" />
        <button type="submit" disabled={!cEmail || !cPass}>Anmelden</button>
        <button type="button" class="ghost" disabled={!cEmail || cPass.length < 8} onclick={() => cloudLogin(true)}>Konto erstellen</button>
      </form>
      <p class="muted small">Passwort mit mindestens 8 Zeichen. Gespeichert wird nur ein Anmeldeschlüssel.</p>
    {/if}
  </section>

  {#if !cloud && !web}
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
  {/if}

  {#if !web}
  <section>
    <h2>Sicherungen</h2>
    <p class="muted">Beim Beenden sichert Muisti automatisch. Vor jedem Wiederherstellen und jeder Übernahme wird der aktuelle Stand zusätzlich gesichert.</p>
    {#if prefs}
      <div class="fields" oninput={savePrefs} onchange={savePrefs}>
        <label>Höchstens alle (Minuten)<input type="number" min="5" bind:value={prefs.backups.minimum_interval_mins} /></label>
        <label>Tägliche behalten<input type="number" min="0" bind:value={prefs.backups.daily} /></label>
        <label>Wöchentliche behalten<input type="number" min="0" bind:value={prefs.backups.weekly} /></label>
        <label>Monatliche behalten<input type="number" min="0" bind:value={prefs.backups.monthly} /></label>
      </div>
    {/if}
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
    <p class="muted">Ein Klick, und Claude kann deine Karten anlegen, durchsuchen und bearbeiten. Frag danach einfach: „Erstelle 10 Karten zu Integralrechnung im Stapel Analysis II.“</p>
    {#if claude?.unstable_location}
      <p class="choice">Verschiebe Muisti zuerst in den Ordner <b>Programme</b> und öffne es von dort. Sonst zeigt Claude ins Leere, sobald die App verschoben wird.</p>
    {/if}
    {#if claude}
      <ul class="clients">
        {#each CLIENTS as c}
          {@const st = claude[c.key]}
          <li>
            <div>
              <b>{c.name}</b>
              <span class="state {st.state}">{!st.installed ? 'nicht installiert' : st.state === 'on' ? 'verbunden' : st.state === 'outdated' ? 'Pfad veraltet' : 'nicht verbunden'}</span>
              <p class="muted small">{c.hint}</p>
            </div>
            {#if st.state === 'on'}
              <button class="ghost sm" onclick={() => disconnect(c.key)}>Trennen</button>
            {:else}
              <button class="sm" disabled={!st.installed || connecting === c.key} onclick={() => connect(c.key)}>
                {connecting === c.key ? 'Verbinde …' : st.state === 'outdated' ? 'Aktualisieren' : 'Verbinden'}
              </button>
            {/if}
          </li>
        {/each}
      </ul>
      <details>
        <summary class="muted small">Andere MCP-Clients</summary>
        <div class="cmd"><code>{claude.command}</code><button class="plain sm" aria-label="Befehl kopieren" onclick={() => copy(claude.command)}><Copy size={16} /></button></div>
      </details>
    {/if}
  </section>

  <section>
    <h2>Speicherort</h2>
    <p class="muted">Hier liegen deine Karten, Medien und Sicherungen. Du kannst einen anderen Ordner wählen, z. B. eine externe Festplatte.</p>
    {#if storage}
      <div class="cmd"><code>{storage.dir}</code><button class="plain sm" aria-label="Pfad kopieren" onclick={() => copy(storage.dir)}><Copy size={16} /></button></div>
      {#if storage.synced_folder}
        <p class="choice">Dieser Ordner wird von einem Cloud-Dienst synchronisiert (OneDrive, iCloud, Dropbox …). Das kann die geöffnete Datenbank beschädigen. Für den Abgleich zwischen Geräten ist AnkiWeb sicherer.</p>
      {/if}
      <div class="row">
        <button class="ghost" disabled={moving} onclick={chooseFolder}>Anderen Ordner wählen …</button>
        {#if !storage.is_default}
          <button class="plain" disabled={moving} onclick={() => applyStorage('move', storage.default)}>Zurück zum Standardordner</button>
        {/if}
      </div>
      {#if moveTarget}
        <div class="choice">
          <b>{moveTarget.folder}</b>
          {#if moveTarget.synced_folder}<p>Achtung: Dieser Ordner wird von einem Cloud-Dienst synchronisiert, das kann die Datenbank beschädigen.</p>{/if}
          {#if moveTarget.has_collection}
            <p>Dort liegt bereits eine Sammlung. Muisti kann sie öffnen; deine aktuelle Sammlung bleibt unverändert am alten Ort.</p>
            <div class="row">
              <button disabled={moving} onclick={() => applyStorage('open')}>Vorhandene Sammlung öffnen</button>
              <button class="ghost" onclick={() => (moveTarget = null)}>Abbrechen</button>
            </div>
          {:else}
            <p>Deine Sammlung wird mit Medien und Sicherungen dorthin kopiert und ab sofort dort verwendet. Die alten Dateien bleiben als Kopie liegen.</p>
            <div class="row">
              <button disabled={moving} onclick={() => applyStorage('move')}>{moving ? 'Kopiere …' : 'Hierhin verschieben'}</button>
              <button class="ghost" onclick={() => (moveTarget = null)}>Abbrechen</button>
            </div>
          {/if}
        </div>
      {/if}
    {/if}
  </section>

  {/if}

  <section>
    <h2>Version</h2>
    <div class="row">
      <span class="num">Muisti {version}</span>
      <button class="ghost sm" disabled={checking} onclick={lookForUpdate}>{checking ? 'Suche …' : 'Nach Updates suchen'}</button>
    </div>
    <p class="muted small">{web ? 'Gibt es eine neue Version, erscheint links „Aktualisieren“: ein Klick lädt die Seite neu.' : 'Die App sucht beim Start selbst nach neuen Versionen. Deine Karten bleiben beim Update unberührt.'}</p>
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
  .extras { display: flex; flex-direction: column; gap: 14px; }
  .seg { display: inline-flex; align-self: flex-start; border: 1px solid var(--rule-2); border-radius: var(--radius); padding: 2px; }
  .seg button { background: transparent; color: var(--ink-2); border: 0; height: 30px; padding: 0 12px; font-weight: 500; }
  .seg button.on { background: var(--ink); color: var(--paper); }
  .extra { display: flex; gap: 12px; align-items: flex-start; font-size: 14px; }
  .extra input { margin-top: 3px; }
  .extra span { display: flex; flex-direction: column; gap: 2px; max-width: 62ch; }
  .extra small { font-size: 13px; }
  .row span { margin-right: 8px; }
  .login { display: flex; gap: 8px; flex-wrap: wrap; }
  .login input { flex: 1 1 200px; }
  .choice { background: var(--warn-bg); color: var(--warn-ink); border-radius: 10px; padding: 14px 16px; display: flex; flex-direction: column; gap: 8px; }
  .choice p { font-size: 14px; }
  .cmd { display: flex; align-items: center; gap: 8px; background: var(--paper-2); border-radius: var(--radius); padding: 8px 8px 8px 12px; }
  .cmd code { flex: 1; font: 13px/1.5 ui-monospace, 'SF Mono', Menlo, Consolas, monospace; overflow-wrap: anywhere; }
  .w { width: 1%; white-space: nowrap; }
  .fields { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
  .fields label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--ink-2); }
  .fields small { font-size: 12px; color: var(--ink-3); }
  .checks { display: flex; flex-direction: column; gap: 8px; }
  label.check { display: flex; align-items: center; gap: 10px; font-size: 14px; }
  .clients { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; }
  .clients li { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 12px 0; border-bottom: 1px solid var(--rule); }
  .clients li:last-child { border-bottom: 0; }
  .clients b { margin-right: 8px; }
  .state { font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 99px; background: var(--paper-3); color: var(--ink-2); }
  .state.on { background: color-mix(in srgb, var(--m-green) 16%, var(--paper)); color: var(--m-green); }
  .state.outdated { background: var(--warn-bg); color: var(--warn-ink); }
  details summary { cursor: pointer; margin-bottom: 8px; }
  .choice b { overflow-wrap: anywhere; }
</style>
