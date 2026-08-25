// =====================================================================
// 🔎 SEARCH ANALYTICS — per-client search intelligence, in THREE TABS
// =====================================================================
//   🌐 All searches   — everything together (blue, 3D radar hero)
//   ⌨️ Search box     — only typed searches (emerald, big daily chart)
//   🤖 AI Assistant   — only chat-driven searches (violet, radar hero)
// Every tab: live tiles, top searches, recent table, its own Excel export.
// All data is isolated per client — the switcher pills pick whose world.
// =====================================================================
import { useEffect, useRef, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid,
} from 'recharts'
import { Stat, PageTitle, Panel, TT, accumulate, trimTail } from '../ui.jsx'
import { getSearchAnalytics } from '../api.js'

const TABS = [
  { id: 'all',       icon: '🌐', label: 'All searches',
    color: '#5f95ff', dim: 'rgba(95,149,255,',
    btn: 'bg-blue-600/30 border-blue-400/50 text-blue-100',
    desc: 'every search from every door — search box and AI chat together' },
  { id: 'search',    icon: '⌨️', label: 'Search box',
    color: '#34d399', dim: 'rgba(52,211,153,',
    btn: 'bg-emerald-600/30 border-emerald-400/50 text-emerald-100',
    desc: 'only what shoppers typed into the search box themselves' },
  { id: 'assistant', icon: '🤖', label: 'AI Assistant',
    color: '#a78bfa', dim: 'rgba(167,139,250,',
    btn: 'bg-violet-600/30 border-violet-400/50 text-violet-100',
    desc: 'only searches the AI chat ran for shoppers ("show me something cheaper…")' },
]

// ---------------------------------------------------------------------
// 🌐 3D SEARCH RADAR — recent queries orbit a pulsing core in 3D space.
// Each dot = one search; size = products found; red = found nothing.
// ---------------------------------------------------------------------
function SearchRadar({ recent, color, dim }) {
  const ref = useRef(null)
  const stateRef = useRef({ recent: [], color, dim })
  stateRef.current = { recent: recent || [], color, dim }

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let raf, t = 0
    const draw = () => {
      const w = canvas.clientWidth, h = canvas.clientHeight
      if (canvas.width !== w * 2) { canvas.width = w * 2; canvas.height = h * 2; ctx.scale(2, 2) }
      ctx.clearRect(0, 0, w, h)
      // fill the WHOLE panel: wide ellipses, not a small circle in the middle
      const cx = w / 2, cy = h / 2
      const Rx = w / 2 - 40, Ry = h / 2 - 16
      const DIM = stateRef.current.dim
      t += 0.008

      for (let i = 1; i <= 3; i++) {
        ctx.beginPath()
        ctx.ellipse(cx, cy, (Rx * i) / 3, (Ry * i) / 3, 0, 0, Math.PI * 2)
        ctx.strokeStyle = DIM + '0.14)'
        ctx.stroke()
      }
      const grad = ctx.createConicGradient ? ctx.createConicGradient(t * 1.6, cx, cy) : null
      if (grad) {
        grad.addColorStop(0, DIM + '0.25)')
        grad.addColorStop(0.12, DIM + '0)')
        grad.addColorStop(1, DIM + '0)')
        ctx.beginPath()
        ctx.ellipse(cx, cy, Rx, Ry, 0, 0, Math.PI * 2)
        ctx.fillStyle = grad
        ctx.fill()
      }
      const pulse = 10 + Math.sin(t * 3) * 2.5
      const core = ctx.createRadialGradient(cx, cy, 1, cx, cy, pulse * 2.4)
      core.addColorStop(0, 'rgba(52,211,153,0.95)')
      core.addColorStop(1, 'rgba(52,211,153,0)')
      ctx.beginPath(); ctx.arc(cx, cy, pulse * 2.4, 0, Math.PI * 2)
      ctx.fillStyle = core; ctx.fill()

      stateRef.current.recent.slice(0, 18).forEach((s, i) => {
        const ring = 1 + (i % 3)
        const ang = t * (0.5 + ring * 0.22) + (i * 2.399)
        const x = cx + Math.cos(ang) * (Rx * ring) / 3
        const y = cy + Math.sin(ang) * (Ry * ring) / 3
        const depth = (Math.sin(ang) + 1) / 2
        const size = Math.min(6, 2 + Math.log1p(s.total || 0)) * (0.6 + depth * 0.7)
        ctx.beginPath(); ctx.arc(x, y, size, 0, Math.PI * 2)
        ctx.fillStyle = s.total === 0
          ? `rgba(248,113,113,${0.35 + depth * 0.6})`
          : DIM + `${0.3 + depth * 0.65})`
        ctx.fill()
        if (depth > 0.75 && s.query) {
          ctx.font = '10px system-ui'
          ctx.fillStyle = `rgba(199,216,255,${(depth - 0.75) * 3.2})`
          // labels flip to the left near the right edge so they never clip
          const label = String(s.query).slice(0, 16)
          ctx.textAlign = x > w - 110 ? 'right' : 'left'
          ctx.fillText(label, x > w - 110 ? x - size - 3 : x + size + 3, y + 3)
          ctx.textAlign = 'left'
        }
      })
      raf = requestAnimationFrame(draw)
    }
    draw()
    return () => cancelAnimationFrame(raf)
  }, [])
  return <canvas ref={ref} className="w-full h-full block" />
}

const fmtMoney = v => '$' + Number(v || 0).toFixed(v && v < 0.01 ? 6 : 4)
const ago = iso => {
  if (!iso) return ''
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  if (s < 60) return `${Math.max(1, Math.round(s))}s ago`
  if (s < 3600) return `${Math.round(s / 60)}m ago`
  if (s < 86400) return `${Math.round(s / 3600)}h ago`
  return `${Math.round(s / 86400)}d ago`
}

export default function SearchAnalyticsPage({ selClient, selClientObj }) {
  const [tab, setTab] = useState('all')
  const [d, setD] = useState(null)
  const [counts, setCounts] = useState({})       // tab badges: {all: n, search: n, assistant: n}
  const [busyCsv, setBusyCsv] = useState(false)
  const T = TABS.find(x => x.id === tab) || TABS[0]

  // active tab data (10s live poll)
  useEffect(() => {
    let alive = true
    setD(null)
    const load = () => getSearchAnalytics(30, tab).then(x => alive && setD(x)).catch(() => {})
    load()
    const id = setInterval(load, 10000)
    return () => { alive = false; clearInterval(id) }
  }, [selClient, tab])

  // badge counts for all three tabs (30s poll)
  useEffect(() => {
    let alive = true
    const load = () => Promise.all(TABS.map(t => getSearchAnalytics(1, t.id).catch(() => null)))
      .then(rs => alive && setCounts(Object.fromEntries(rs.map((r, i) => [TABS[i].id, r?.total ?? '…']))))
    load()
    const id = setInterval(load, 30000)
    return () => { alive = false; clearInterval(id) }
  }, [selClient])

  const downloadExcel = async () => {
    setBusyCsv(true)
    try {
      const full = await getSearchAnalytics(1000, tab)
      const rows = full.recent || []
      const esc = v => `"${String(v ?? '').replace(/"/g, '""')}"`
      const csv = ['Time,Search,Source,Products found,Speed (ms),From cache,AI tokens,AI cost ($)']
        .concat(rows.map(r => [r.at, r.query, r.source, r.total, r.took_ms,
          r.cached ? 'yes' : 'no', r.tokens, r.cost].map(esc).join(',')))
        .join('\n')
      const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `${tab}-searches-${selClient}-${new Date().toISOString().slice(0, 10)}.csv`
      a.click()
      URL.revokeObjectURL(a.href)
    } catch { /* nothing to download */ }
    setBusyCsv(false)
  }

  const top = d?.top || []
  const recent = d?.recent || []
  // 📈 growing total — the bars climb and never fall back to the floor
  const daily = accumulate(trimTail(d?.daily || [], 'count'), ['count'])
  const maxTop = Math.max(1, ...top.map(x => x.count))
  const clientName = selClientObj?.name || selClient
  const noun = tab === 'assistant' ? 'AI conversation' : 'search'
  const nouns = tab === 'assistant' ? 'AI conversations' : 'searches'

  return (
    <div>
      <PageTitle icon="🔎" title="Search Analytics"
                 desc={`What shoppers look for on ${clientName}'s site — recorded live, isolated per client, exportable.`} />

      {/* ---------- the three doors ---------- */}
      <div className="flex gap-2 flex-wrap mb-4">
        {TABS.map(x => (
          <button key={x.id} onClick={() => setTab(x.id)}
                  className={`px-4 py-2 rounded-xl text-sm font-semibold transition border flex items-center gap-2 ${
                    tab === x.id ? x.btn : 'bg-white/5 text-slate-400 border-white/10 hover:bg-white/10'}`}>
            <span>{x.icon}</span>{x.label}
            <span className={`text-[11px] px-2 py-0.5 rounded-full ${tab === x.id ? 'bg-black/25' : 'bg-white/10'}`}>
              {counts[x.id] ?? '…'}
            </span>
          </button>
        ))}
      </div>
      <div className="text-xs text-slate-500 mb-4">{T.icon} {T.desc}</div>

      {/* ---------- headline numbers ---------- */}
      <div className="grid grid-cols-1 xs:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-4">
        <Stat label={tab === 'assistant' ? 'AI conversations' : 'Total searches'}
              value={d == null ? '…' : d.total} sub="all time, this client only"
              accent="text-cyan-400" />
        <Stat label="Today" value={d == null ? '…' : d.today}
              sub={`${nouns} since midnight UTC`} accent="text-emerald-400" />
        <Stat label="Avg answer speed" value={d == null ? '…' : `${Math.round(d.avg_ms)} ms`}
              sub={tab === 'assistant' ? 'per AI-run search' : 'per search, incl. AI'}
              accent="text-violet-400" />
        <Stat label="Found nothing" value={d == null ? '…' : d.zero_results}
              sub="catalogue gaps to fix!"
              accent={d?.zero_results ? 'text-amber-400' : 'text-emerald-400'} />
        <Stat label="AI cost" value={d == null ? '…' : fmtMoney(d.cost)}
              sub={`${d?.ai_calls || 0} AI calls · ${d?.tokens || 0} tokens`} accent="text-amber-400" />
      </div>

      {/* ---------- hero visuals: each tab has its own look ---------- */}
      {tab === 'search' ? (
        /* ⌨️ Search-box tab: one BIG emerald rhythm chart */
        <Panel title="📈 Typed searches — growing total (the shop's search heartbeat)" className="mb-4 h-72 card-in">
          <ResponsiveContainer width="100%" height="88%">
            <BarChart data={daily} margin={{ top: 6, right: 8, left: -22, bottom: 0 }}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="date" tickLine={false} axisLine={false}
                     tickFormatter={v => (v || '').slice(5)} minTickGap={20} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={46} />
              <Tooltip {...TT} />
              <Bar dataKey="count" name="searches" fill={T.color}
                   radius={[5, 5, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </Panel>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
          <Panel title={`${T.icon} Live ${noun} radar — each dot is real`} className="h-72 card-in">
            <div className="h-full relative">
              {recent.length
                ? <SearchRadar key={tab} recent={recent} color={T.color} dim={T.dim} />
                : <div className="absolute inset-0 flex items-center justify-center text-sm text-slate-500">
                    nothing here yet — it comes alive within seconds of the first {noun}
                  </div>}
              <div className="absolute bottom-1 left-1 text-[10px] text-slate-500">
                ⬤ found products · 🔴 found nothing · size = results · front = newest sweep
              </div>
            </div>
          </Panel>
          <Panel title={`📈 ${tab === 'assistant' ? 'AI conversations' : 'Searches'} — growing total (14 days)`}
                 className="h-72 card-in">
            <ResponsiveContainer width="100%" height="88%">
              <BarChart data={daily} margin={{ top: 6, right: 8, left: -22, bottom: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="date" tickLine={false} axisLine={false}
                       tickFormatter={v => (v || '').slice(5)} minTickGap={20} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={46} />
                <Tooltip {...TT} />
                <Bar dataKey="count" name={nouns} fill={T.color}
                     radius={[5, 5, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </Panel>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* ---------- top searches ---------- */}
        <Panel title={`🏆 Top ${tab === 'assistant' ? 'AI requests' : 'searches'}`}
               className="lg:col-span-2 card-in tilt-3d">
          {top.length ? (
            <div className="space-y-2">
              {top.map((x, i) => (
                <div key={x.query} className="relative rounded-lg overflow-hidden border border-white/5">
                  <div className="absolute inset-y-0 left-0 transition-all duration-700"
                       style={{ width: `${(x.count / maxTop) * 100}%`, background: T.dim + '0.18)' }} />
                  <div className="relative flex items-center justify-between px-3 py-2 text-sm">
                    <span className="truncate pr-2">
                      <span className="text-slate-500 mr-2">{i + 1}.</span>{x.query}
                    </span>
                    <span className="text-xs text-slate-400 whitespace-nowrap">
                      ×{x.count} · finds ~{x.avg_found}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : <div className="text-sm text-slate-500 py-4">nothing yet for this client</div>}
        </Panel>

        {/* ---------- recent + Excel ---------- */}
        <Panel className="lg:col-span-3 card-in" title={`🕐 Recent ${nouns}`}
               right={
                 <button onClick={downloadExcel} disabled={busyCsv || !recent.length}
                         className="text-xs px-3 py-1.5 rounded-lg bg-emerald-600/30 border border-emerald-400/40 text-emerald-200 hover:bg-emerald-500/40 transition disabled:opacity-40 font-semibold whitespace-nowrap shrink-0">
                   {busyCsv ? 'building…' : '⬇️ Download Excel (CSV)'}
                 </button>}>
          {recent.length ? (
            <div className="overflow-x-auto max-h-80 overflow-y-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-slate-400 text-xs border-b border-white/10 sticky top-0 bg-[#0d1020]">
                    <th className="text-left py-2 pr-3">Search</th>
                    {tab === 'all' && <th className="text-left pr-3">Door</th>}
                    <th className="text-right pr-3">Found</th>
                    <th className="text-right pr-3">Speed</th>
                    <th className="text-right pr-3">AI cost</th>
                    <th className="text-right">When</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((r, i) => (
                    <tr key={i} className="border-b border-white/5 hover:bg-white/5 transition">
                      <td className="py-2 pr-3 max-w-[220px] truncate">
                        {r.total === 0 && <span title="found nothing">🔴 </span>}{r.query}
                      </td>
                      {tab === 'all' &&
                        <td className="pr-3 text-xs">{r.source === 'assistant'
                          ? <span className="text-violet-300">🤖 AI</span>
                          : <span className="text-emerald-300">⌨️ box</span>}</td>}
                      <td className={`text-right pr-3 tabular ${r.total === 0 ? 'text-red-400' : 'text-slate-300'}`}>{r.total}</td>
                      <td className="text-right pr-3 text-xs text-slate-400 tabular">
                        {Math.round(r.took_ms)} ms{r.cached ? ' ⚡' : ''}
                      </td>
                      <td className="text-right pr-3 text-xs text-amber-300/80 tabular">
                        {r.tokens ? fmtMoney(r.cost) : '—'}
                      </td>
                      <td className="text-right text-xs text-slate-500 whitespace-nowrap">{ago(r.at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <div className="text-sm text-slate-500 py-4">
                no {nouns} recorded yet — they appear here within seconds
              </div>}
          <div className="text-[11px] text-slate-600 mt-3">
            ⚡ = answered from cache (no AI cost) · Excel contains up to the last 1,000 rows of THIS
            tab for {clientName} only — other clients are physically filtered out.
          </div>
        </Panel>
      </div>
    </div>
  )
}
