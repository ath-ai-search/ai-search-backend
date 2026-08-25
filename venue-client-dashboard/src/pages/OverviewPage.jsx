// =====================================================================
// 📊 OVERVIEW — the store at a glance: KPIs, the growing activity line
// (totals only climb — never a dead floor), and the top searches.
// =====================================================================
import { useEffect, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
         CartesianGrid } from 'recharts'
import { getOverview } from '../api.js'
import { Panel, PageTitle, Stat, Badge, Skeleton, TT,
         fmtRev, padDaily, accumulate } from '../ui.jsx'

export default function OverviewPage() {
  const [ov, setOv] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    let dead = false
    const load = () => getOverview()
      .then(d => { if (!dead) { setOv(d); setErr('') } })
      .catch(ex => { if (!dead) setErr(String(ex.message || ex)) })
    load()
    const t = setInterval(load, 30000)
    return () => { dead = true; clearInterval(t) }
  }, [])

  if (err) return <div className="text-coral text-sm">⚠️ {err}</div>
  if (!ov) return <div className="space-y-3">
    <Skeleton h={90} /><Skeleton h={260} /><Skeleton h={200} /></div>

  // growing totals — each day stacks on the days before it
  const daily = accumulate(
    padDaily(ov.daily || [], 14, ['clicks', 'orders', 'impressions']),
    ['clicks', 'orders', 'impressions'])

  return (
    <div>
      <PageTitle icon="📊" title="Overview"
                 desc="Your AI search, live — every number is from real shoppers." />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <Stat label="Products indexed" value={ov.products}
              sub="searchable right now" />
        <Stat label="Search clicks" value={ov.clicks_total}
              sub={`${ov.today?.click || 0} today`} />
        <Stat label="Orders from search" value={ov.orders_total} accent="text-sand"
              sub={`${ov.today?.purchase || 0} today`} />
        <Stat label="Search revenue" value={fmtRev(ov.revenue_total)} accent="text-sand"
              sub={`${fmtRev(ov.revenue_month)} this month`} />
      </div>

      <Panel title="📈 Activity — running totals, last 14 days"
             right={<Badge tone={ov.live_5m > 0 ? 'mint' : 'slate'}>
               ● {ov.live_5m} events / 5 min</Badge>} className="mb-4">
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={daily} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
              <defs>
                <linearGradient id="gClicks" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6d4aff" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#6d4aff" stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="gOrders" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#e0821f" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#e0821f" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(120,120,160,0.15)" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }}
                     tickFormatter={d => d.slice(5)} />
              <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
              <Tooltip {...TT} />
              <Area type="linear" dataKey="clicks" name="clicks (total)"
                    stroke="#6d4aff" strokeWidth={2.5} fill="url(#gClicks)" />
              <Area type="linear" dataKey="orders" name="orders (total)"
                    stroke="#e0821f" strokeWidth={2.5} fill="url(#gOrders)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="text-[11px] text-mist mt-2">
          Lines show the running total — they only climb as your store earns.
        </div>
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Panel title="🔎 Top searches">
          {(ov.top || []).length === 0 && (
            <div className="text-xs text-mist py-6 text-center">
              No searches tracked yet — they appear as shoppers use the search box.
            </div>
          )}
          <div className="space-y-1.5">
            {(ov.top || []).map((t, i) => (
              <div key={i} className="flex items-center gap-3 rounded-lg px-3 py-2
                   bg-white/[0.03] border border-white/5">
                <span className="text-mist text-xs w-4">{i + 1}</span>
                <span className="flex-1 text-sm truncate">“{t.query}”</span>
                <span className="text-xs text-mint">{t.clicks} clicks</span>
                {t.orders > 0 && (
                  <span className="text-xs text-sand">{t.orders} orders
                    · {fmtRev(t.revenue)}</span>
                )}
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="⚡ Today so far">
          <div className="grid grid-cols-2 gap-3">
            {[['🔎 Clicks', ov.today?.click || 0],
              ['🛒 Add to cart', ov.today?.add_to_cart || 0],
              ['💰 Purchases', ov.today?.purchase || 0],
              ['👀 Impressions', ov.today?.impression || 0]].map(([l, v]) => (
              <div key={l} className="rounded-xl bg-white/[0.03] border border-white/5
                   px-3 py-3 text-center">
                <div className="text-xl font-extrabold text-foam tabular">{v}</div>
                <div className="text-[11px] text-mist mt-0.5">{l}</div>
              </div>
            ))}
          </div>
          <div className="text-[11px] text-mist mt-3">
            {ov.queries_total} different search phrases tried by shoppers overall.
          </div>
        </Panel>
      </div>
    </div>
  )
}
