// =====================================================================
// 🧩 UI KIT — the portal's shared building blocks (ocean/aurora family)
// =====================================================================
import { useEffect, useRef, useState } from 'react'

export const TT = {
  contentStyle: {
    background: 'var(--tt-bg, #ffffff)', border: '1px solid rgba(109,74,255,0.30)',
    borderRadius: 12, fontSize: 12, color: 'var(--tt-ink, #201d33)',
    boxShadow: '0 12px 30px -10px rgba(20,16,43,0.25)',
  },
  labelStyle: { color: 'var(--tt-mut, #6b6a8a)' },
  itemStyle: { color: 'var(--tt-ink, #201d33)' },
  cursor: { fill: 'rgba(109,74,255,0.06)' },
}

/* count-up number — the "alive" feeling on every KPI */
export function useCountUp(value, ms = 700) {
  const [shown, setShown] = useState(0)
  const prev = useRef(0)
  useEffect(() => {
    const from = prev.current, to = Number(value) || 0
    prev.current = to
    if (from === to) { setShown(to); return }
    const t0 = performance.now()
    let raf
    const step = (t) => {
      const k = Math.min(1, (t - t0) / ms)
      setShown(from + (to - from) * (1 - Math.pow(1 - k, 3)))
      if (k < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [value, ms])
  return shown
}

export function Stat({ label, value, sub, accent = 'text-mint', animate = true }) {
  const n = typeof value === 'number'
  const shown = useCountUp(n ? value : 0)
  return (
    <div className="bg-tide border border-white/10 rounded-card p-4 tilt-3d card-in">
      <div className="text-[11px] uppercase tracking-wider text-mist">{label}</div>
      <div className={`text-2xl font-extrabold mt-1 tabular break-words ${accent}`}>
        {n && animate ? Math.round(shown).toLocaleString() : value}
      </div>
      {sub && <div className="text-[11px] text-mist mt-1">{sub}</div>}
    </div>
  )
}

export function Panel({ title, right, children, className = '' }) {
  return (
    <div className={`bg-tide border border-white/10 rounded-card p-4 card-in ${className}`}>
      {(title || right) && (
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="text-sm text-foam flex items-center gap-2 min-w-0">
            <span className="w-1.5 h-1.5 rounded-full bg-mint/80 shrink-0" />
            {title}
          </div>
          {right && <div className="shrink-0">{right}</div>}
        </div>
      )}
      {children}
    </div>
  )
}

export function PageTitle({ icon, title, desc }) {
  return (
    <div className="mb-5">
      <h1 className="text-xl font-extrabold flex items-center gap-2">
        <span>{icon}</span>{title}
      </h1>
      {desc && <div className="text-xs text-mist mt-1 max-w-2xl">{desc}</div>}
    </div>
  )
}

export function Badge({ tone = 'mint', children }) {
  const tones = {
    mint:  'bg-mint/15 text-mint border-mint/30',
    sand:  'bg-sand/15 text-sand border-sand/30',
    coral: 'bg-coral/15 text-coral border-coral/30',
    mist:  'bg-white/5 text-mist border-white/10',
  }
  return (
    <span className={`text-[11px] px-2 py-0.5 rounded-full border ${tones[tone] || tones.mint}`}>
      {children}
    </span>
  )
}

export function Skeleton({ h = 16, w = '100%', className = '' }) {
  return <div className={`skeleton ${className}`} style={{ height: h, width: w }} />
}

/* 💡 friendly page explainer — floating icon, 3D hover, simple words */
export function ExplainCard({ icon, title = 'What is this page?', lines = [], example }) {
  return (
    <div className="mt-4 rounded-card border border-mint/25 bg-tide p-5 card-in tilt-3d">
      <div className="flex items-start gap-5">
        <div className="text-5xl blu-float select-none leading-none pt-1">{icon}</div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-extrabold text-foam mb-2">💡 {title}</div>
          <ul className="space-y-1.5">
            {lines.map(l => (
              <li key={l} className="text-xs text-mist flex gap-2">
                <span className="text-mint shrink-0">✓</span><span>{l}</span>
              </li>
            ))}
          </ul>
          {example && (
            <div className="mt-3 text-xs bg-white border border-mint/25 rounded-xl
                            px-3.5 py-2.5 text-foam leading-relaxed">
              <span className="font-bold text-teal">Example: </span>{example}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export const fmtMoney = (v) =>
  '$' + Number(v || 0).toFixed(3)   // exactly 3 digits after the dollar

/* store money (revenue) — whole dollars and cents, not AI micro-cents */
export const fmtRev = (v) =>
  '$' + Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })

/* fill missing calendar days with zeros — 2 real points make an ugly
   straight line; a padded series shows the TRUE story (quiet, then spikes) */
export function padDaily(rows, days = 14, keys = ['count']) {
  const byDate = Object.fromEntries((rows || []).map(r => [r.date, r]))
  const out = []
  const now = new Date()
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(),
                                now.getUTCDate() - i))
    const key = d.toISOString().slice(0, 10)
    out.push(byDate[key] ||
      { date: key, ...Object.fromEntries(keys.map(k => [k, 0])) })
  }
  // ⚠️ boss rule: a chart must NEVER end plunging to zero (a half-finished
  // "today" looked like the business dying). Trim empty days off the END;
  // quiet days in the MIDDLE stay — that part is the true story.
  const isZero = (r) => Object.entries(r).every(([k, v]) => k === 'date' || !v)
  while (out.length > 2 && isZero(out[out.length - 1])) out.pop()
  // ...and never START with a long dead floor either: drop leading empty
  // days, keeping exactly ONE so the line still rises from zero
  while (out.length > 2 && isZero(out[0]) && isZero(out[1])) out.shift()
  return out
}

/* ✂️ drop the empty tail — a half-finished "today" (or the current hour)
   made the line dive to the floor at the right edge. Quiet days in the
   MIDDLE stay: that part is the true story. */
export function trimTail(rows, key = 'count') {
  const out = [...(rows || [])]
  while (out.length > 2 && !Number(out[out.length - 1]?.[key])) out.pop()
  return out
}

/* running totals — the line only ever goes UP (never dips back to zero):
   each day adds on top of the days before it */
export function accumulate(rows, keys = ['count']) {
  const acc = Object.fromEntries(keys.map(k => [k, 0]))
  return (rows || []).map(r => {
    const out = { ...r }
    for (const k of keys) {
      acc[k] += Number(r[k]) || 0
      out[k] = Math.round(acc[k] * 1e6) / 1e6
    }
    return out
  })
}

export const ago = (iso) => {
  if (!iso) return '—'
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  if (s < 60) return `${Math.max(1, Math.round(s))}s ago`
  if (s < 3600) return `${Math.round(s / 60)}m ago`
  if (s < 86400) return `${Math.round(s / 3600)}h ago`
  return `${Math.round(s / 86400)}d ago`
}
