// =====================================================================
// 💰 BILLING — their REAL money numbers (indexing runs + search AI),
// month by month, with a cost forecast. No invented prices.
// =====================================================================
import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid,
  PieChart, Pie, Cell,
} from 'recharts'
import { getBilling } from '../api.js'
import { Stat, Panel, PageTitle, Skeleton, fmtMoney, TT, ExplainCard, accumulate, trimTail } from '../ui.jsx'

export default function BillingPage() {
  const [d, setD] = useState(null)
  useEffect(() => {
    let alive = true
    getBilling().then(x => alive && setD(x)).catch(() => {})
    return () => { alive = false }
  }, [])

  const cur = d?.current || {}
  const months = d?.months || []
  // simple honest forecast: current daily average × days in month
  const now = new Date()
  const dayOfMonth = now.getUTCDate()
  const daysInMonth = new Date(now.getUTCFullYear(), now.getUTCMonth() + 1, 0).getDate()
  const forecast = dayOfMonth > 0
    ? (cur.total_cost || 0) / dayOfMonth * daysInMonth : 0

  return (
    <div>
      <PageTitle icon="💰" title="Billing"
                 desc="Every cent is computed from your real usage — nothing estimated, nothing invented." />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <Stat label={`This month (${d?.this_month || '…'})`}
              value={d ? fmtMoney(cur.total_cost) : '…'}
              sub={`${(cur.ingest_calls || 0) + (cur.search_calls || 0)} AI calls`}
              accent="text-mint" animate={false} />
        <Stat label="Indexing cost" value={d ? fmtMoney(cur.ingest_cost) : '…'}
              sub={`${cur.ingest_calls || 0} products embedded`} accent="text-teal" animate={false} />
        <Stat label="Search AI cost" value={d ? fmtMoney(cur.search_cost) : '…'}
              sub={`${cur.search_calls || 0} AI searches`} accent="text-foam" animate={false} />
        <Stat label="Month-end forecast" value={d ? fmtMoney(forecast) : '…'}
              sub="at your current pace" accent="text-sand" animate={false} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <Panel title="🥧 Where the money goes" className="h-64">
          {d === null ? <Skeleton h={160} /> : (cur.total_cost || 0) > 0 ? (
            <ResponsiveContainer width="100%" height="84%">
              <PieChart>
                <Pie data={[
                       { name: '🧠 Indexing (embeddings)', value: cur.ingest_cost || 0 },
                       { name: '🔎 Search AI', value: cur.search_cost || 0 },
                     ].filter(x => x.value > 0)}
                     dataKey="value" nameKey="name" innerRadius="52%" outerRadius="78%"
                     paddingAngle={4} isAnimationActive={false}
                     label={({ percent }) => `${Math.round(percent * 100)}%`}>
                  <Cell fill="#5b3bd6" stroke="#ffffff" />
                  <Cell fill="#e0821f" stroke="#ffffff" />
                </Pie>
                <Tooltip {...TT} formatter={(v) => fmtMoney(v)} />
              </PieChart>
            </ResponsiveContainer>
          ) : <div className="h-full flex items-center justify-center text-sm text-mist">
                no costs yet this month</div>}
        </Panel>
        <Panel title="📊 Cost per month" className="h-64 lg:col-span-2">
          {d === null ? <Skeleton h={160} /> : months.length ? (
            <ResponsiveContainer width="100%" height="84%">
              <BarChart data={[...months].reverse()} margin={{ top: 6, right: 8, left: -14, bottom: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="month" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} width={58}
                       tick={false} />
                <Tooltip {...TT} formatter={(v) => fmtMoney(v)} />
                <Bar dataKey="ingest_cost" name="Indexing" stackId="c" fill="#5b3bd6"
                     isAnimationActive={false} />
                <Bar dataKey="search_cost" name="Search AI" stackId="c" fill="#e0821f"
                     radius={[5, 5, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          ) : <div className="text-sm text-mist py-4">no billed activity yet</div>}
        </Panel>
      </div>

      <Panel title="🧾 Your sync runs (each one is a billing record)">
        {d === null ? <Skeleton h={140} /> : (d.runs || []).length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-mist text-xs border-b border-white/10">
                  <th className="text-left py-2 pr-3">Finished</th>
                  <th className="text-right pr-3">Products</th>
                  <th className="text-right pr-3">AI tokens</th>
                  <th className="text-right pr-3">Cost</th>
                  <th className="text-right">Duration</th>
                </tr>
              </thead>
              <tbody>
                {(d.runs || []).slice(0, 12).map((r, i) => (
                  <tr key={i} className="border-b border-white/5 hover:bg-white/5 transition">
                    <td className="py-2 pr-3 text-xs whitespace-nowrap">{(r.finished_at || '').replace('T', ' ').slice(0, 16)}</td>
                    <td className="text-right pr-3 tabular">{r.indexed}</td>
                    <td className="text-right pr-3 tabular text-mist">{(r.tokens || 0).toLocaleString()}</td>
                    <td className="text-right pr-3 tabular text-sand">{fmtMoney(r.cost)}</td>
                    <td className="text-right text-xs text-mist">{Math.round(r.elapsed_sec || 0)}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <div className="text-sm text-mist py-3">no sync runs yet</div>}
      </Panel>

      {/* 🧮 unit economics + daily cost rhythm */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
        <Panel title="🧮 Your unit economics">
          <div className="space-y-4 py-1">
            <div>
              <div className="text-[11px] uppercase tracking-wider text-mist">
                cost per product indexed</div>
              <div className="text-xl font-extrabold text-teal tabular">
                {cur.ingest_calls ? fmtMoney(cur.ingest_cost / cur.ingest_calls) : '—'}</div>
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-wider text-mist">
                cost per AI search</div>
              <div className="text-xl font-extrabold text-sand tabular">
                {cur.search_calls ? fmtMoney(cur.search_cost / cur.search_calls) : '—'}</div>
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-wider text-mist">
                AI tokens this month</div>
              <div className="text-xl font-extrabold text-mint tabular">
                {((cur.ingest_tokens || 0) + (cur.search_tokens || 0)).toLocaleString()}</div>
            </div>
          </div>
        </Panel>
        <Panel title="📈 Indexing cost — growing total (14 days)" className="h-72 lg:col-span-2">
          {d === null ? <Skeleton h={160} /> : (d.recent_days || []).length ? (
            <ResponsiveContainer width="100%" height="84%">
              <BarChart data={accumulate(
                          trimTail([...(d.recent_days || [])].reverse(), 'ingest_cost'),
                          ['ingest_cost'])}
                        margin={{ top: 6, right: 8, left: -8, bottom: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="date" tickLine={false} axisLine={false}
                       tickFormatter={v => (v || '').slice(5)} minTickGap={22} />
                <YAxis tickLine={false} axisLine={false} width={62}
                       tick={false} />
                <Tooltip {...TT} formatter={(v) => fmtMoney(v)} />
                <Bar dataKey="ingest_cost" name="indexing cost so far" fill="#5b3bd6"
                     radius={[5, 5, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          ) : <div className="h-full flex items-center justify-center text-sm text-mist">
                costs appear day by day as you sync</div>}
        </Panel>
      </div>

      {/* 🧾 how the bill is built — simple and honest */}
      <Panel title="🧾 How your bill is built" className="mt-4">
        <div className="flex flex-col lg:flex-row items-stretch gap-3">
          {[['📦', 'You sync products', 'each product is sent to the AI once'],
            ['🧠', 'AI reads every one', 'reading uses tokens (tiny fractions of a cent)'],
            ['🔎', 'Shoppers search', 'AI-powered searches also use a few tokens'],
            ['🧾', 'Tokens × price = bill', 'no fixed fee, no minimum — only real usage']]
            .map(([ic, t, sub], i) => (
            <div key={t} className="flex-1 flex items-center gap-3">
              <div className="flex-1 rounded-xl border border-mint/20 bg-mint/5 p-4
                   text-center tilt-3d">
                <div className="text-3xl mb-1 blu-float"
                     style={{ animationDelay: `${i * 0.4}s` }}>{ic}</div>
                <div className="text-sm font-bold text-foam">{t}</div>
                <div className="text-[11px] text-mist mt-1">{sub}</div>
              </div>
              {i < 3 && <div className="hidden lg:block text-mint text-xl pulse-dot"
                             style={{ animationDelay: `${i * 0.3}s` }}>→</div>}
            </div>
          ))}
        </div>
      </Panel>

      <ExplainCard icon="💰"
        lines={[
          'This page shows the REAL cost of your AI search — computed from usage, never invented.',
          'Indexing cost happens when products sync; Search AI cost happens when shoppers search.',
          'The forecast simply continues your current pace to the end of the month.',
        ]}
        example={'You sync 500 products once (~$0.003) and shoppers make thousands of searches — most searches are cached, so the bill stays tiny.'} />
    </div>
  )
}
