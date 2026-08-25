// =====================================================================
// 🔎 SEARCH ANALYTICS — the 3-door view of THEIR searches:
//   🌐 All · ⌨️ Search box · 🤖 AI Assistant
// with the live 3D radar, per-day chart, top list, recent table, Excel.
// =====================================================================
import { useEffect, useRef, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid,
  LineChart, Line, PieChart, Pie, Cell,
} from 'recharts'
import { getAnalytics } from '../api.js'
import { Stat, Panel, PageTitle, Skeleton, fmtMoney, fmtRev, ago, TT, padDaily, accumulate } from '../ui.jsx'

const TABS = [
  { id: 'all', icon: '🌐', label: 'All searches', color: '#6d4aff', dim: 'rgba(109,74,255,' },
  { id: 'search', icon: '⌨️', label: 'Search box', color: '#5b3bd6', dim: 'rgba(91,59,214,' },
  { id: 'assistant', icon: '🤖', label: 'AI Assistant', color: '#e0821f', dim: 'rgba(224,130,31,' },
]

/* live radar — every dot a real search of THIS client */
function Radar({ recent, dim }) {
  const ref = useRef(null)
  const stateRef = useRef({ recent: [], dim })
  stateRef.current = { recent: recent || [], dim }
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
      const Rx = w / 2 - 28, Ry = h / 2 - 18
      const DIM = stateRef.current.dim
      t += 0.008
      for (let i = 1; i <= 3; i++) {
        ctx.beginPath()
        ctx.ellipse(cx, cy, (Rx * i) / 3, (Ry * i) / 3, 0, 0, Math.PI * 2)
        ctx.strokeStyle = DIM + '0.15)'; ctx.stroke()
      }
      const grad = ctx.createConicGradient ? ctx.createConicGradient(t * 1.6, cx, cy) : null
      if (grad) {
        grad.addColorStop(0, DIM + '0.25)'); grad.addColorStop(0.12, DIM + '0)')
        grad.addColorStop(1, DIM + '0)')
        ctx.beginPath(); ctx.ellipse(cx, cy, Rx, Ry, 0, 0, Math.PI * 2)
        ctx.fillStyle = grad; ctx.fill()
      }
      const pulse = 9 + Math.sin(t * 3) * 2.2
      const core = ctx.createRadialGradient(cx, cy, 1, cx, cy, pulse * 2.4)
      core.addColorStop(0, 'rgba(109,74,255,0.85)'); core.addColorStop(1, 'rgba(109,74,255,0)')
      ctx.beginPath(); ctx.arc(cx, cy, pulse * 2.4, 0, Math.PI * 2)
      ctx.fillStyle = core; ctx.fill()
      stateRef.current.recent.slice(0, 18).forEach((s, i) => {
        const ring = 1 + (i % 3)
        const ang = t * (0.5 + ring * 0.22) + i * 2.399
        const x = cx + Math.cos(ang) * (Rx * ring) / 3
        const y = cy + Math.sin(ang) * (Ry * ring) / 3
        const depth = (Math.sin(ang) + 1) / 2
        const size = Math.min(6, 2 + Math.log1p(s.total || 0)) * (0.6 + depth * 0.7)
        ctx.beginPath(); ctx.arc(x, y, size, 0, Math.PI * 2)
        ctx.fillStyle = s.total === 0
          ? `rgba(255,143,125,${0.35 + depth * 0.6})` : DIM + `${0.3 + depth * 0.65})`
        ctx.fill()
        if (depth > 0.75 && s.query) {
          ctx.font = '10px system-ui'
          const ink = document.documentElement.classList.contains('dark')
            ? '217,213,238' : '32,29,51'
          ctx.fillStyle = `rgba(${ink},${(depth - 0.75) * 3.2})`
          ctx.fillText(String(s.query).slice(0, 16), x + size + 3, y + 3)
        }
      })
      raf = requestAnimationFrame(draw)
    }
    draw()
    return () => cancelAnimationFrame(raf)
  }, [])
  return <canvas ref={ref} className="w-full h-full block" />
}

const WINDOWS = [{ id: 7, label: '7d' }, { id: 30, label: '30d' }, { id: 0, label: 'All' }]
const PIE_COLORS = ['#6d4aff', '#5b3bd6', '#9b7bff', '#e0821f', '#dd5c46', '#a29ec4']

export default function AnalyticsPage() {
  const [tab, setTab] = useState('all')
  const [win, setWin] = useState(30)
  const [d, setD] = useState(null)
  const [busyCsv, setBusyCsv] = useState(false)
  const T = TABS.find(x => x.id === tab) || TABS[0]

  useEffect(() => {
    let alive = true
    setD(null)
    const load = () => getAnalytics(tab, 30, win).then(x => alive && setD(x)).catch(() => {})
    load()
    const id = setInterval(load, 10000)
    return () => { alive = false; clearInterval(id) }
  }, [tab, win])

  const downloadExcel = async () => {
    setBusyCsv(true)
    try {
      const full = await getAnalytics(tab, 1000, win)
      const rows = full.recent || []
      const esc = v => `"${String(v ?? '').replace(/"/g, '""')}"`
      const csv = ['Time,Search,Source,Products found,Speed (ms),AI cost ($)']
        .concat(rows.map(r => [r.at, r.query, r.source, r.total, r.took_ms, r.cost]
          .map(esc).join(','))).join('\n')
      const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `${tab}-searches-${new Date().toISOString().slice(0, 10)}.csv`
      a.click(); URL.revokeObjectURL(a.href)
    } catch { /* nothing */ }
    setBusyCsv(false)
  }

  const recent = d?.recent || []
  const top = d?.top || []
  const maxTop = Math.max(1, ...top.map(x => x.count))

  return (
    <div>
      <PageTitle icon="🔎" title="Search Analytics"
                 desc="Every search on your site — live, and yours alone." />
      <div className="flex gap-2 flex-wrap mb-4 items-center">
        {TABS.map(x => (
          <button key={x.id} onClick={() => setTab(x.id)}
                  className={`px-4 py-2 rounded-xl text-sm font-semibold border transition ${
                    tab === x.id
                      ? 'bg-mint/20 border-mint/50 text-foam'
                      : 'bg-white/5 border-white/10 text-mist hover:bg-white/10'}`}>
            {x.icon} {x.label}
          </button>
        ))}
        {/* 📆 time window — like a real analytics tool */}
        <div className="ml-auto flex rounded-xl border border-white/10 overflow-hidden">
          {WINDOWS.map(w => (
            <button key={w.id} onClick={() => setWin(w.id)}
                    className={`px-3.5 py-2 text-sm font-bold transition ${
                      win === w.id ? 'bg-mint text-white'
                                   : 'bg-white/5 text-mist hover:bg-white/10'}`}>
              {w.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4 mb-4">
        <Stat label={tab === 'assistant' ? 'AI conversations' : 'Total searches'}
              value={d?.total ?? '…'} sub="all time" />
        <Stat label="Today" value={d?.today ?? '…'} sub="since midnight UTC" accent="text-teal" />
        <Stat label="Avg speed" value={d ? `${Math.round(d.avg_ms)} ms` : '…'}
              sub="per search" accent="text-foam" animate={false} />
        <Stat label="Found nothing" value={d?.zero_results ?? '…'} sub="see Overview 💎"
              accent={d?.zero_results ? 'text-coral' : 'text-mint'} />
        <Stat label="AI cost" value={d ? fmtMoney(d.cost) : '…'}
              sub={`${d?.ai_calls || 0} AI calls`} accent="text-sand" animate={false} />
      </div>

      {/* 💵 the shopping story — only where product events exist */}
      {tab !== 'assistant' && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
          <Stat label="Product clicks" value={d?.clicks ?? '…'}
                sub="from search results" accent="text-teal" />
          <Stat label="Orders" value={d?.orders ?? '…'}
                sub="purchases after searching" accent="text-foam" />
          <Stat label="Revenue" value={d ? fmtRev(d.revenue) : '…'}
                sub="earned by search" accent="text-mint" animate={false} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <Panel title={`${T.icon} Live radar`} className="h-64">
          <div className="h-[calc(100%-2.25rem)] relative">
            {d === null ? <Skeleton h={160} /> : recent.length
              ? <Radar key={tab} recent={recent} dim={T.dim} />
              : <div className="absolute inset-0 flex items-center justify-center
                                text-sm text-mist">it comes alive with the first search</div>}
          </div>
        </Panel>
        <Panel title={`📈 Searches — growing total (${win ? `${win} days` : 'all time'})`}
               className="h-64">
          {d === null ? <Skeleton h={160} /> : (
            <ResponsiveContainer width="100%" height="84%">
              <LineChart data={accumulate(padDaily(d.daily, win || 14))}
                         margin={{ top: 6, right: 8, left: -8, bottom: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="date" tickLine={false} axisLine={false}
                       tickFormatter={v => (v || '').slice(5)} minTickGap={20} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={40}
                       tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k` : v} />
                <Tooltip {...TT} />
                <Line type="linear" dataKey="count" name="searches" stroke={T.color}
                      strokeWidth={2.5} dot={{ r: 2.5, fill: T.color, strokeWidth: 0 }}
                      activeDot={{ r: 5 }} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Panel>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* 🥧 share of demand — top searches vs the rest */}
        <Panel title="🥧 Demand share" className="lg:col-span-2 h-80">
          {d === null ? <Skeleton h={200} /> : top.length ? (
            <ResponsiveContainer width="100%" height="92%">
              <PieChart>
                <Pie data={[
                       ...top.slice(0, 5).map(x => ({ name: x.query, value: x.count })),
                       ...(d.total > top.slice(0, 5).reduce((s, x) => s + x.count, 0)
                         ? [{ name: 'other searches',
                              value: d.total - top.slice(0, 5).reduce((s, x) => s + x.count, 0) }]
                         : []),
                     ]}
                     dataKey="value" nameKey="name" innerRadius="52%" outerRadius="78%"
                     paddingAngle={3} isAnimationActive={false}
                     label={({ percent }) => `${Math.round(percent * 100)}%`}
                     labelLine={{ stroke: 'rgba(32,29,51,0.25)' }}>
                  {PIE_COLORS.map((c, i) => <Cell key={i} fill={c} stroke="#ffffff" />)}
                </Pie>
                <Tooltip {...TT} />
              </PieChart>
            </ResponsiveContainer>
          ) : <div className="text-sm text-mist py-3">nothing yet</div>}
        </Panel>

        <Panel title="🏆 Top searches" className="lg:col-span-3 tilt-3d">
          {d === null ? <Skeleton h={160} /> : top.length ? (
            <div className="space-y-2">
              {top.map((x, i) => (
                <div key={x.query} className="relative rounded-lg overflow-hidden border border-white/5">
                  <div className="absolute inset-y-0 left-0 transition-all duration-700"
                       style={{ width: `${(x.count / maxTop) * 100}%`, background: T.dim + '0.16)' }} />
                  <div className="relative flex items-center justify-between px-3 py-2 text-sm">
                    <span className="truncate pr-2">
                      <span className="text-mist mr-2">{i + 1}.</span>{x.query}</span>
                    <span className="text-xs text-mist whitespace-nowrap">
                      ×{x.count}
                      {x.ctr_pct !== undefined && ` · ${x.ctr_pct}% click`}
                      {x.revenue > 0 && <span className="text-mint"> · {fmtRev(x.revenue)}</span>}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : <div className="text-sm text-mist py-3">nothing yet</div>}
        </Panel>

        <Panel className="lg:col-span-5" title="🕐 Recent searches"
               right={<button onClick={downloadExcel} disabled={busyCsv || !recent.length}
                              className="text-xs px-3 py-1.5 rounded-lg bg-mint/20 border
                                         border-mint/40 text-mint hover:bg-mint/30 transition
                                         disabled:opacity-40 font-semibold">
                 {busyCsv ? 'building…' : '⬇️ Download Excel'}</button>}>
          {d === null ? <Skeleton h={160} /> : recent.length ? (
            <div className="overflow-x-auto max-h-80 overflow-y-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-mist text-xs border-b border-white/10 sticky top-0 bg-tide">
                    <th className="text-left py-2 pr-3">Search</th>
                    <th className="text-right pr-3">Found</th>
                    <th className="text-right pr-3">Speed</th>
                    <th className="text-right">When</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((r, i) => (
                    <tr key={i} className="border-b border-white/5 hover:bg-white/5 transition">
                      <td className="py-2 pr-3 max-w-[240px] truncate">
                        {r.total === 0 && '🔴 '}{r.query}</td>
                      <td className={`text-right pr-3 tabular ${r.total === 0 ? 'text-coral' : ''}`}>
                        {r.total}</td>
                      <td className="text-right pr-3 text-xs text-mist tabular">
                        {Math.round(r.took_ms)} ms{r.cached ? ' ⚡' : ''}</td>
                      <td className="text-right text-xs text-mist whitespace-nowrap">{ago(r.at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <div className="text-sm text-mist py-3">no searches recorded yet</div>}
        </Panel>
      </div>
    </div>
  )
}
