// =====================================================================
// 📊 OVERVIEW — the 3D constellation of THEIR catalogue + living KPIs,
// 14-day rhythm chart, top searches, and the found-nothing gold list.
// =====================================================================
import { useEffect, useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid,
} from 'recharts'
import { getOverview, getMe, getBilling, getAnalytics, getEvents } from '../api.js'
import { Stat, Panel, PageTitle, Badge, Skeleton, fmtMoney, fmtRev, ago, TT, padDaily, accumulate } from '../ui.jsx'
import { SearchGlobe } from '../three3d.jsx'
import ReportPDF from '../ReportPDF.jsx'

/* one glowing funnel step — width shows how many survived the step */
function FunnelBar({ label, value, base, color, sub }) {
  const w = base > 0 ? Math.max(4, (value / base) * 100) : 4
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-mist">{label}</span>
        <span className="text-foam tabular font-semibold">{(value || 0).toLocaleString()}
          {sub && <span className="text-mist font-normal"> · {sub}</span>}</span>
      </div>
      <div className="h-6 rounded-lg bg-white/5 overflow-hidden">
        <div className="h-full rounded-lg transition-all duration-700"
             style={{ width: `${w}%`, background: color }} />
      </div>
    </div>
  )
}

export default function OverviewPage({ client, goTo }) {
  const [d, setD] = useState(null)
  const [me, setMe] = useState(null)
  const [report, setReport] = useState(null)
  const [busyPdf, setBusyPdf] = useState(false)

  useEffect(() => {
    let alive = true
    const load = () => {
      getOverview().then(x => alive && setD(x)).catch(() => {})
      getMe().then(x => alive && setMe(x)).catch(() => {})
    }
    load()
    const id = setInterval(load, 30000)
    return () => { alive = false; clearInterval(id) }
  }, [])

  // 🧾 gather everything fresh, then hand over to the browser's Save-as-PDF
  const downloadPdf = async () => {
    if (busyPdf) return
    setBusyPdf(true)
    try {
      const [overview, billing, analytics, meFresh, events] = await Promise.all([
        getOverview(), getBilling(), getAnalytics('all', 30), getMe(),
        getEvents('all', 10).catch(() => null)])
      setReport({ client, me: meFresh, overview, billing, analytics, events })
      const old = document.title
      document.title = `VenueMarketplace-report-${client?.client_id || 'client'}-${
        new Date().toISOString().slice(0, 10)}`
      setTimeout(() => { window.print(); document.title = old }, 150)
    } catch { /* data endpoints already surface errors elsewhere */ }
    setBusyPdf(false)
  }

  const doctorOk = me?.doctor?.last_search_at &&
    (Date.now() - new Date(me.doctor.last_search_at).getTime()) < 48 * 3600e3

  return (
    <div>
      <PageTitle icon="📊" title={`Welcome back, ${client?.name || client?.client_id}`}
                 desc="Your AI search, live — every number is yours alone." />
      <ReportPDF data={report} />

      {/* ---------- top row: globe box · quick view · doctor ---------- */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        {/* 🌍 the globe — ONE compact box, admin-dashboard style */}
        <div className="h-80 relative overflow-hidden rounded-card border card-in"
             style={{ borderColor: '#2c2260', background:
               'linear-gradient(165deg, #1c1546 0%, #130e30 55%, #0a081f 100%)' }}>
          <div className="absolute inset-0">
            <SearchGlobe />
          </div>
          <div className="absolute top-3 left-4 right-4 text-[11px] text-[#a99fe0]">
            your catalogue, alive in the AI index
          </div>
          <div className="absolute bottom-3.5 left-4">
            <div className="text-4xl font-extrabold text-white leading-none">
              {me?.products?.toLocaleString?.() || '…'}</div>
            <div className="text-[11px] text-[#b9b0e8] mt-1">products indexed</div>
          </div>
        </div>

        {/* ⚡ quick view — the chips grew into a real panel */}
        <Panel title="⚡ Quick view" className="h-80">
          <div className="flex flex-col justify-between h-[calc(100%-2rem)] py-1">
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-xl bg-mint/10
                              border border-mint/25 px-4 py-3">
                <span className="text-xs text-mist flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-mint pulse-dot" />
                  searching right now</span>
                <span className="text-xl font-extrabold text-mint tabular">
                  {d?.live_5m ?? 0}</span>
              </div>
              <div className="flex items-center justify-between rounded-xl bg-sand/10
                              border border-sand/30 px-4 py-3">
                <span className="text-xs text-mist">revenue this month</span>
                <span className="text-xl font-extrabold text-sand tabular">
                  {fmtRev(d?.funnel?.revenue)}</span>
              </div>
              <div className="flex items-center justify-between rounded-xl bg-white/5
                              border border-white/10 px-4 py-3">
                <span className="text-xs text-mist">searches today</span>
                <span className="text-xl font-extrabold text-foam tabular">
                  {d?.searches_today ?? 0}</span>
              </div>
            </div>
            <button onClick={downloadPdf} disabled={busyPdf}
                    className="w-full rounded-xl bg-mint hover:bg-teal text-white
                               font-extrabold py-3 text-sm transition disabled:opacity-50">
              {busyPdf ? 'building…' : '🧾 Download PDF report'}</button>
          </div>
        </Panel>

        <Panel title="🩺 Integration doctor" className="h-80">
          {me === null ? <Skeleton h={120} /> : (
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full pulse-dot ${doctorOk ? 'bg-mint' : 'bg-coral'}`} />
                {doctorOk ? 'Your site is talking to us' : 'No searches seen recently'}
              </div>
              <div className="text-xs text-mist">
                Last search: <span className="text-foam">{ago(me?.doctor?.last_search_at)}</span></div>
              <div className="text-xs text-mist">
                Last product sync: <span className="text-foam">
                  {me?.doctor?.last_sync
                    ? `${me.doctor.last_sync.indexed} products · ${ago(me.doctor.last_sync.finished_at)}`
                    : 'none yet'}</span></div>
              <div className="text-xs text-mist">Plan: <Badge tone="sand">
                {(me?.plan?.max_products || 0).toLocaleString()} products max</Badge></div>
              <button onClick={() => goTo('widget')}
                      className="text-xs text-mint hover:underline">→ installation & keys</button>
            </div>
          )}
        </Panel>
      </div>

      {/* ---------- 💵 the money row — what search EARNED them ---------- */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <Stat label="Revenue from search" value={d ? fmtRev(d.funnel?.revenue) : '…'}
              sub={`this month · ${fmtRev(d?.revenue_total)} all time`}
              accent="text-mint" animate={false} />
        <Stat label="Product clicks" value={d?.clicks_total ?? '…'}
              sub={`${d?.ctr_pct ?? 0}% of searches click`} accent="text-teal" />
        <Stat label="Orders from search" value={d?.orders_total ?? '…'}
              sub={`${d?.conv_pct ?? 0}% search → order`} accent="text-foam" />
        <Stat label="AI cost this month" value={d ? fmtMoney(d.ai_cost_month) : '…'}
              sub={`${d?.ai_tokens_month?.toLocaleString?.() || 0} tokens`}
              accent="text-sand" animate={false} />
      </div>

      {/* ---------- KPIs ---------- */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <Stat label="Products live" value={d?.products ?? '…'} sub="in your search index" />
        <Stat label="Searches today" value={d?.searches_today ?? '…'}
              sub={`${d?.searches_total?.toLocaleString?.() || '…'} all time`} accent="text-teal" />
        <Stat label="Right now" value={d?.live_5m ?? '…'} sub="searches, last 5 min"
              accent="text-mint" />
        <Stat label="Found nothing" value={d?.zero_count ?? '…'}
              sub="chances to sell more ↓" accent={d?.zero_count ? 'text-coral' : 'text-mint'} />
      </div>

      {/* ---------- funnel + 14-day rhythm ---------- */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <Panel title="🧲 Conversion funnel — this month" className="h-72">
          {d === null ? <Skeleton h={160} /> : (
            <div className="space-y-2.5 pt-1">
              <FunnelBar label="Searches" value={d.funnel?.searches}
                         base={d.funnel?.searches} color="#6d4aff" />
              <FunnelBar label="Product clicks" value={d.funnel?.clicks}
                         base={d.funnel?.searches} color="#5b3bd6"
                         sub={d.funnel?.searches
                           ? `${Math.round((d.funnel.clicks / d.funnel.searches) * 100)}%` : null} />
              <FunnelBar label="Orders" value={d.funnel?.orders}
                         base={d.funnel?.searches} color="#e0821f"
                         sub={d.funnel?.revenue ? fmtRev(d.funnel.revenue) : null} />
              <div className="text-[11px] text-mist pt-1">
                counted from real click &amp; purchase events on your site
              </div>
            </div>
          )}
        </Panel>
        <Panel title="📈 Searches · clicks · orders — growing total (14 days)" className="h-72 lg:col-span-2">
          {d === null ? <Skeleton h={160} /> : (
            <ResponsiveContainer width="100%" height="84%">
              <AreaChart data={accumulate(
                padDaily(d.daily, 14, ['count', 'assistant', 'clicks', 'orders', 'revenue']),
                ['count', 'assistant', 'clicks', 'orders'])}
                         margin={{ top: 6, right: 8, left: -8, bottom: 0 }}>
                <defs>
                  <linearGradient id="gAll" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6d4aff" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#6d4aff" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="gClk" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#5b3bd6" stopOpacity={0.22} />
                    <stop offset="100%" stopColor="#5b3bd6" stopOpacity={0.02} />
                  </linearGradient>
                  <linearGradient id="gAi" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#e0821f" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#e0821f" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="date" tickLine={false} axisLine={false}
                       tickFormatter={v => (v || '').slice(5)} minTickGap={24} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={44}
                       tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k` : v} />
                <Tooltip {...TT} />
                <Area type="linear" dataKey="count" name="searches" stroke="#6d4aff"
                      strokeWidth={2} fill="url(#gAll)" isAnimationActive={false} />
                <Area type="linear" dataKey="clicks" name="clicks" stroke="#5b3bd6"
                      strokeWidth={2} fill="url(#gClk)" isAnimationActive={false} />
                <Area type="linear" dataKey="orders" name="orders" stroke="#e0821f"
                      strokeWidth={2} fill="url(#gAi)" isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Panel>
      </div>

      {/* ---------- top + zero ---------- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Panel title="🏆 What shoppers search most">
          {d === null ? <Skeleton h={140} /> : d.top?.length ? (
            <div className="space-y-2">
              {d.top.map((x, i) => (
                <div key={x.query} className="flex items-center justify-between text-sm
                     rounded-lg px-3 py-2 bg-white/[0.03] border border-white/5">
                  <span className="truncate pr-2">
                    <span className="text-mist mr-2">{i + 1}.</span>{x.query}</span>
                  <span className="text-xs text-mist whitespace-nowrap">
                    ×{x.count} · finds ~{x.avg_found}</span>
                </div>
              ))}
            </div>
          ) : <div className="text-sm text-mist py-3">no searches yet — they appear live</div>}
        </Panel>
        <Panel title="💎 Found nothing — what shoppers WANT but you don't sell"
               right={<button onClick={() => goTo('search-settings')}
                              className="text-xs text-mint hover:underline">fix with synonyms →</button>}>
          {d === null ? <Skeleton h={140} /> : d.zero_top?.length ? (
            <div className="space-y-2">
              {d.zero_top.map(x => (
                <div key={x.query} className="flex items-center justify-between text-sm
                     rounded-lg px-3 py-2 bg-coral/5 border border-coral/20">
                  <span className="truncate pr-2">🔴 {x.query}</span>
                  <span className="text-xs text-mist">asked ×{x.count}</span>
                </div>
              ))}
            </div>
          ) : <div className="text-sm text-mint py-3">✨ every search found products — perfect</div>}
        </Panel>
      </div>
    </div>
  )
}
