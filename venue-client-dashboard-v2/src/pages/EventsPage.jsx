// =====================================================================
// 🛰️ LIVE ACTIVITY — every shopper move on their site, the moment it
// happens: clicks, add-to-carts, wishlists, purchases (with money).
// Auto-refreshes; each chip filters the feed. Their events only.
// =====================================================================
import { useEffect, useState } from 'react'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import { getEvents } from '../api.js'
import { Stat, Panel, PageTitle, Skeleton, fmtRev, ago, TT, accumulate, trimTail } from '../ui.jsx'

const MIX_COLORS = { click: '#5b3bd6', add_to_cart: '#e0821f', wishlist: '#dd5c46',
                     purchase: '#6d4aff', view: '#a29ec4', impression: '#cdc7e4' }

const TYPES = [
  { id: 'all',         icon: '🌐', label: 'Everything' },
  { id: 'click',       icon: '🖱️', label: 'Clicks' },
  { id: 'add_to_cart', icon: '🛒', label: 'Carts' },
  { id: 'wishlist',    icon: '❤️', label: 'Wishlist' },
  { id: 'purchase',    icon: '✅', label: 'Purchases' },
  { id: 'view',        icon: '👁️', label: 'Views' },
  { id: 'impression',  icon: '📡', label: 'Impressions' },
]
const LOOK = {
  click:       { icon: '🖱️', label: 'clicked',      cls: 'bg-teal/10 text-teal border-teal/30' },
  add_to_cart: { icon: '🛒', label: 'added to cart', cls: 'bg-sand/10 text-sand border-sand/30' },
  wishlist:    { icon: '❤️', label: 'wishlisted',    cls: 'bg-coral/10 text-coral border-coral/30' },
  purchase:    { icon: '✅', label: 'BOUGHT',        cls: 'bg-mint/15 text-mint border-mint/40' },
  view:        { icon: '👁️', label: 'viewed',        cls: 'bg-white/5 text-mist border-white/10' },
  impression:  { icon: '📡', label: 'saw in results', cls: 'bg-white/5 text-mist border-white/10' },
}

export default function EventsPage() {
  const [type, setType] = useState('all')
  const [d, setD] = useState(null)

  useEffect(() => {
    let alive = true
    setD(null)
    const load = () => getEvents(type, 60).then(x => alive && setD(x))
      .catch(() => alive && setD(x => x || { counts: {}, today: {}, recent: [] }))
    load()
    const id = setInterval(load, 8000)
    return () => { alive = false; clearInterval(id) }
  }, [type])

  const today = d?.today || {}
  const counts = d?.counts || {}
  const recent = d?.recent || []

  return (
    <div>
      <PageTitle icon="🛰️" title="Live activity"
                 desc="Every move a shopper makes on your site — as it happens, yours alone." />

      {/* today's story */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4 mb-4">
        <Stat label="Live now" value={d?.live_5m ?? '…'} sub="events, last 5 min"
              accent="text-mint" />
        <Stat label="Clicks today" value={today.click ?? 0} sub="products opened"
              accent="text-teal" />
        <Stat label="Carts today" value={today.add_to_cart ?? 0} sub="add-to-cart"
              accent="text-sand" />
        <Stat label="Purchases today" value={today.purchase ?? 0} sub="from search"
              accent="text-foam" />
        <Stat label="Revenue today" value={d ? fmtRev(d.today_revenue) : '…'}
              sub="from tracked purchases" accent="text-mint" animate={false} />
      </div>

      {/* type chips with all-time counts */}
      <div className="flex gap-2 flex-wrap mb-4">
        {TYPES.map(t => (
          <button key={t.id} onClick={() => setType(t.id)}
                  className={`px-3.5 py-2 rounded-xl text-sm font-semibold border transition ${
                    type === t.id
                      ? 'bg-mint/20 border-mint/50 text-foam'
                      : 'bg-white/5 border-white/10 text-mist hover:bg-white/10'}`}>
            {t.icon} {t.label}
            {t.id !== 'all' && counts[t.id] !== undefined &&
              <span className="ml-1.5 text-[11px] opacity-70">{counts[t.id]}</span>}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* 🥧 what shoppers DO — the activity mix */}
      <Panel title="🥧 Activity mix" className="h-fit">
        {d === null ? <Skeleton h={200} /> : Object.keys(counts).length ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={TYPES.filter(t => t.id !== 'all' && counts[t.id])
                       .map(t => ({ name: `${t.icon} ${t.label}`, id: t.id,
                                    value: counts[t.id] }))}
                     dataKey="value" nameKey="name" innerRadius="50%" outerRadius="76%"
                     paddingAngle={3} isAnimationActive={false}
                     label={({ percent }) => `${Math.round(percent * 100)}%`}
                     labelLine={{ stroke: 'rgba(32,29,51,0.25)' }}>
                  {TYPES.filter(t => t.id !== 'all' && counts[t.id]).map(t => (
                    <Cell key={t.id} fill={MIX_COLORS[t.id] || '#a29ec4'} stroke="#ffffff" />
                  ))}
                </Pie>
                <Tooltip {...TT} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="min-h-[380px] flex flex-col items-center justify-center gap-3">
            <div className="text-4xl opacity-40">🥧</div>
            <div className="text-sm text-mist text-center px-4">
              the pie fills up as shoppers click, cart and buy
            </div>
          </div>
        )}
      </Panel>

      {/* the feed */}
      <Panel className="lg:col-span-2"
             title={<span className="flex items-center gap-2">📜 The feed
              <span className="w-2 h-2 rounded-full bg-mint pulse-dot" />
              <span className="text-[11px] text-mist font-normal">refreshes every 8s</span>
            </span>}>
        {d === null ? <Skeleton h={220} /> : recent.length ? (
          <div className="space-y-1.5 min-h-[380px] max-h-[560px] overflow-y-auto pr-1">
            {recent.map((e, i) => {
              const L = LOOK[e.type] || LOOK.view
              return (
                <div key={i} className="flex items-center gap-3 text-sm rounded-xl px-3
                     py-2 bg-white/[0.03] border border-white/5 hover:bg-white/5 transition">
                  <span className={`text-[11px] px-2 py-0.5 rounded-full border shrink-0
                        font-semibold ${L.cls}`}>{L.icon} {L.label}</span>
                  <span className="flex-1 min-w-0 truncate">
                    {e.product_name || (e.product_id ? `product ${e.product_id}` : '—')}
                    {e.query && <span className="text-mist text-xs">
                      {'  '}· searched “{e.query}”</span>}
                  </span>
                  {e.value > 0 && e.type === 'purchase' &&
                    <span className="text-mint font-bold text-xs shrink-0">
                      +{fmtRev(e.value)}</span>}
                  <span className="text-[11px] text-mist whitespace-nowrap shrink-0">
                    {ago(e.at)}</span>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="min-h-[380px] flex flex-col items-center justify-center gap-5">
            <div className="text-sm text-mist text-center">
              🌙 Quiet right now — events appear here the moment a shopper clicks,
              carts or buys on your site.
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full max-w-2xl">
              {[['1️⃣', 'Search', 'a shopper searches on your website'],
                ['2️⃣', 'Click / cart / buy', 'they open a product, add it, buy it'],
                ['3️⃣', 'It lands HERE', 'in seconds — with the money earned']]
                .map(([n, t, s]) => (
                <div key={t} className="rounded-xl border border-mint/20 bg-mint/5 p-4
                     text-center">
                  <div className="text-xl mb-1">{n}</div>
                  <div className="text-sm font-bold text-foam">{t}</div>
                  <div className="text-[11px] text-mist mt-1">{s}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </Panel>
      </div>

      {/* ⏰ the last 24 hours — when your shop breathes */}
      <Panel title="📈 Activity — growing total (last 24 hours)" className="h-64 mt-4">
        {d === null ? <Skeleton h={160} /> : (d.hourly || []).length ? (
          <ResponsiveContainer width="100%" height="84%">
            <AreaChart data={accumulate(trimTail(d.hourly, 'events'),
                                        ['events', 'clicks', 'orders'])}
                       margin={{ top: 6, right: 8, left: -8, bottom: 0 }}>
              <defs>
                <linearGradient id="gEv" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6d4aff" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#6d4aff" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="hour" tickLine={false} axisLine={false} minTickGap={26} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={40}
                     tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k` : v} />
              <Tooltip {...TT} />
              <Area type="linear" dataKey="events" name="all events" stroke="#6d4aff"
                    strokeWidth={2.5} fill="url(#gEv)" isAnimationActive={false} />
              <Area type="linear" dataKey="clicks" name="clicks" stroke="#5b3bd6"
                    strokeWidth={2} fill="none" isAnimationActive={false} />
              <Area type="linear" dataKey="orders" name="purchases" stroke="#e0821f"
                    strokeWidth={2} fill="none" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-sm text-mist">
            the 24-hour rhythm appears with the first events
          </div>
        )}
      </Panel>
    </div>
  )
}
