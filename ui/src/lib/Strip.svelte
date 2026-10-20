<script>
  // The semester strip: one cell per day. Past = reviews done, today outlined, future = forecast due.
  let { past, future } = $props()
  let width = $state(1000)

  const DAY = 86400000
  const fmt = (d) => d.toLocaleDateString('de-DE', { weekday: 'short', day: 'numeric', month: 'short' })

  const cells = $derived.by(() => {
    const now = new Date()
    now.setHours(12, 0, 0, 0)
    const max = Math.max(1, ...past)
    const all = [
      ...past.map((n, i) => {
        const ago = past.length - 1 - i
        const level = n === 0 ? 0 : Math.min(3, Math.ceil((n / max) * 3))
        return { n, ago, level, kind: ago === 0 ? 'today' : 'past' }
      }),
      ...future.map((n, i) => ({ n, ago: -(i + 1), level: 0, kind: 'future' })),
    ].map((c) => ({ ...c, date: new Date(now.getTime() - c.ago * DAY) }))
    // ponytail: narrow windows drop the oldest days instead of shrinking cells below ~6px
    const fit = Math.max(future.length + 14, Math.floor(width / 9))
    return all.slice(-fit)
  })

  const months = $derived(
    cells
      .flatMap((c, i) => (i === 0 || c.date.getDate() === 1 ? [{ col: i + 1, label: c.date.toLocaleDateString('de-DE', { month: 'long' }) }] : []))
      .filter((m, i, all) => !all[i + 1] || all[i + 1].col - m.col > 10), // drop a cut-off first month
  )

  const tip = (c) =>
    c.kind === 'future' ? `${fmt(c.date)}: ${c.n} Wiederholungen geplant`
    : `${fmt(c.date)}${c.kind === 'today' ? ' (heute)' : ''}: ${c.n} ${c.n === 1 ? 'Karte' : 'Karten'} gelernt`
</script>

<div class="strip-wrap" bind:clientWidth={width}>
  <div class="strip" style:grid-template-columns="repeat({cells.length}, 1fr)" role="img" aria-label="Lernverlauf und Prognose">
    {#each cells as c}
      <i class="l{c.level} {c.kind}" class:has={c.kind === 'future' && c.n > 0} title={tip(c)}></i>
    {/each}
  </div>
  <div class="months" style:grid-template-columns="repeat({cells.length}, 1fr)">
    {#each months as m}<span style:grid-column="{m.col} / span 20">{m.label}</span>{/each}
  </div>
</div>

<style>
  .strip { display: grid; gap: 2px; }
  i { height: 22px; border-radius: 2px; background: var(--paper-3); transition: transform 120ms var(--ease); }
  i:hover { transform: scaleY(1.25); }
  .l1 { background: var(--heat-1); }
  .l2 { background: var(--heat-2); }
  .l3 { background: var(--heat-3); }
  .today { outline: 2px solid var(--paper); box-shadow: 0 0 0 4px var(--ink); z-index: 1; }
  .today.l0 { background: var(--paper-3); }
  .future { background: transparent; border: 1px dashed var(--rule-2); }
  .future.has { border-style: solid; border-color: var(--heat-2); }
  .months { display: grid; font-size: 12px; color: var(--ink-2); margin-top: 8px; }
  .months span { grid-row: 1; white-space: nowrap; }
</style>
