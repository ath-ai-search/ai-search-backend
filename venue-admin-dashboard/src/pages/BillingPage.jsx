// Billing page — monthly AI cost records (stored in the DATABASE) + PDF bills
import { useState, useEffect } from 'react'
import {
  BarChart, Bar, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from 'recharts'
import { Stat, PageTitle, Panel, TT, fmtMoney, accumulate, trimTail } from '../ui.jsx'
// shared base: localhost in dev, same-origin (nginx) in production
import { API, getBillingMonth } from '../api.js'

export default function BillingPage({ billing, selClient }) {
  const b = billing || {}
  const [monthDetail, setMonthDetail] = useState(null)   // clicked month box

  const openMonth = async (m) => {
    try { setMonthDetail(await getBillingMonth(m)) } catch {}
  }
  // stale month popup must never survive a client switch
  useEffect(() => { setMonthDetail(null) }, [selClient])
  const cur = b.current || {}
  const months = b.months || []
  const cloud = b.cloud || {}                       // ☁️ fixed Azure infrastructure cost
  const tco = b.total_cost_of_ownership || {}   // Azure + AI together
  const lastMonth = months.find(m => m.month !== b.this_month)
  const chart = [...months].reverse().map(m => ({ name: m.month, cost: m.total_cost }))

  return (
    <div>
      <PageTitle icon="💰" title="Billing"
                 desc="Every AI cost is recorded per day in the database. Each month makes its own bill — the current month resets automatically, old months stay stored forever." />

      <div className="grid grid-cols-1 xs:grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <Stat label={`This month (${b.this_month || '—'})`} value={fmtMoney(cur.total_cost)}
              sub={`${(cur.ingest_calls || 0) + (cur.search_calls || 0)} AI calls · ${cur.days || 0} active days`} accent="text-emerald-400" />
        <Stat label="Indexing cost" value={fmtMoney(cur.ingest_cost)} sub={`${cur.ingest_calls || 0} calls`} accent="text-cyan-400" />
        <Stat label="Search cost" value={fmtMoney(cur.search_cost)} sub={`${cur.search_calls || 0} calls`} accent="text-violet-400" />
        <Stat label="All-time total" value={fmtMoney(b.all_time_cost)} sub={`${months.length} month(s) on record`} accent="text-amber-400" />
      </div>

      {/* ☁️ AZURE INFRASTRUCTURE — the fixed monthly rent for the server */}
      <Panel title="☁️ Azure infrastructure cost — fixed every month" className="mb-4">
        <div className="text-xs text-slate-500 mb-3">
          This is what the SERVER costs to rent. It does not change with the number of products —
          index 500 or 50,000, the Azure bill stays the same. Only the AI cost above grows with usage.
          <span className="ml-2 text-slate-600">Region: {cloud.region || '—'}</span>
        </div>
        {/* where these numbers came from — live from Azure, or the saved fallback */}
        <div className="text-[11px] mb-3 flex flex-wrap items-center gap-2">
          {String(cloud.source || '').startsWith('live')
            ? <span className="rounded-full bg-emerald-500/15 text-emerald-300 px-2 py-0.5">🟢 LIVE — the server read its own resources and Azure's price list</span>
            : <span className="rounded-full bg-amber-500/15 text-amber-300 px-2 py-0.5">🟡 saved prices — {cloud.source || 'Azure not reachable'}</span>}
          {cloud.updated_at > 0 &&
            <span className="text-slate-600">checked {new Date(cloud.updated_at * 1000).toLocaleString()} · refreshes every 6 h</span>}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* the item list */}
          <div className="lg:col-span-2 overflow-x-auto -mx-2 px-2">
            <table className="w-full text-sm">
              <thead className="text-slate-400 border-b border-white/10">
                <tr>
                  <th className="text-left font-medium py-2">Azure service</th>
                  <th className="text-left font-medium py-2">What it is</th>
                  <th className="text-right font-medium py-2">Per month</th>
                </tr>
              </thead>
              <tbody>
                {(cloud.items || []).map((it, i) => (
                  <tr key={i} className="border-b border-white/5">
                    <td className="py-2 font-semibold text-cyan-300 whitespace-nowrap">{it.service}</td>
                    <td className="py-2 text-slate-400 text-xs">{it.detail}</td>
                    <td className="py-2 text-right text-slate-200">
                      {it.monthly > 0 ? `$${it.monthly.toFixed(2)}` : <span className="text-emerald-400">free</span>}
                    </td>
                  </tr>
                ))}
                <tr>
                  <td className="py-2 font-bold text-slate-200" colSpan={2}>AZURE TOTAL</td>
                  <td className="py-2 text-right font-bold text-cyan-300">
                    ${(cloud.monthly_total ?? 0).toFixed(2)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* total cost of ownership */}
          <div className="rounded-2xl bg-black/25 border border-white/10 p-4">
            <div className="text-xs uppercase tracking-wider text-slate-500 mb-3">
              Total cost of ownership · {tco.month || b.this_month}
            </div>
            <Row label="☁️ Azure (server)" value={`$${(tco.cloud_cost ?? 0).toFixed(2)}`} sub="fixed" color="text-cyan-300" />
            <Row label="🤖 AI (OpenAI)" value={fmtMoney(tco.ai_cost)} sub="per use" color="text-violet-300" />
            <div className="border-t border-white/10 mt-3 pt-3 flex items-end justify-between">
              <span className="text-sm font-semibold text-slate-200">TOTAL</span>
              <span className="text-2xl font-bold text-emerald-400">${(tco.total ?? 0).toFixed(2)}</span>
            </div>
            <div className="text-[10px] text-slate-500 mt-2">
              ≈ ${(cloud.daily_estimate ?? 0).toFixed(2)} per day of infrastructure
            </div>
          </div>
        </div>
      </Panel>

      {/* 📆 MONTHLY CYCLE — click an old month box to see its graph + bill */}
      <Panel title="📆 Monthly cycle — click a month to open it" className="mb-4">
        <div className="text-xs text-slate-500 mb-3">
          Month 1 = indexing + searching. Later months usually have NO indexing cost
          (products already stored!) — only search costs continue. Each new month starts at $0.00
          automatically; old months stay stored forever.
        </div>
        <div className="flex flex-wrap gap-3">
          {months.map(m => (
            <button key={m.month} onClick={() => openMonth(m.month)}
                    className={`rounded-2xl border p-4 text-left min-w-[8.5rem] flex-1 sm:flex-none transition ${
                      monthDetail?.month === m.month
                        ? 'bg-indigo-500/20 border-indigo-400/50'
                        : 'bg-white/5 border-white/10 hover:border-cyan-400/40'}`}>
              <div className="text-xs text-slate-400">{m.month}
                {m.month === b.this_month && <span className="ml-2 text-[10px] bg-emerald-500/20 text-emerald-300 rounded-full px-2 py-0.5">current</span>}
              </div>
              <div className="text-xl font-bold text-emerald-400 mt-1">{fmtMoney(m.total_cost)}</div>
              <div className="text-[10px] text-slate-500 mt-0.5">{m.ingest_calls + m.search_calls} calls · {m.days} day(s)</div>
            </button>
          ))}
          {months.length === 0 && <div className="text-sm text-slate-500">No months on record yet.</div>}
        </div>

        {monthDetail && (
          <div className="mt-4 rounded-2xl bg-black/25 border border-white/10 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <div className="text-sm text-slate-200 font-semibold">📊 {monthDetail.month} — day by day
                <span className="ml-3 text-xs text-slate-400">indexing {fmtMoney(monthDetail.ingest_cost)} · search {fmtMoney(monthDetail.search_cost)} · total <b className="text-emerald-400">{fmtMoney(monthDetail.total_cost)}</b></span>
              </div>
              <a href={`${API}/billing/pdf?month=${monthDetail.month}`}
                 className="text-xs rounded-lg bg-indigo-500/20 text-indigo-300 px-3 py-1.5 hover:bg-indigo-500/30 transition">📄 Download this month's PDF bill</a>
            </div>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={accumulate(
                            trimTail(monthDetail.days, 'ingest_cost'),
                            ['ingest_cost', 'search_cost'])}
                          margin={{ top: 5, right: 10, left: -6, bottom: 0 }}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 10 }} width={70} tickFormatter={fmtMoney} />
                  <Tooltip {...TT} formatter={(v) => fmtMoney(v)} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar isAnimationActive={false} dataKey="ingest_cost" name="Indexing (running total)" stackId="c" fill="#38bdf8" />
                  <Bar isAnimationActive={false} dataKey="search_cost" name="Search (running total)" stackId="c" fill="#a78bfa" radius={[4,4,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </Panel>

      {chart.length > 0 && (
        <Panel title="📊 Cost per month" className="h-64 mb-4">
          <ResponsiveContainer width="100%" height="84%">
            <BarChart data={chart} margin={{ top: 5, right: 10, left: -6, bottom: 0 }}>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
              <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} />
              <YAxis stroke="#64748b" tick={{ fontSize: 10 }} width={70} tickFormatter={fmtMoney} />
              <Tooltip {...TT} formatter={(v) => fmtMoney(v)} />
              <Bar isAnimationActive={false} dataKey="cost" name="Total cost" radius={[4, 4, 0, 0]}>
                {chart.map((_, i) => <Cell key={i} fill={i === chart.length - 1 ? '#34d399' : '#38bdf8'} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Panel>
      )}

      <Panel title="🧾 Monthly bills — download the PDF invoice" className="mb-4">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-400 text-xs border-b border-white/10">
                <th className="text-left py-2 pl-2">Month</th>
                <th className="text-right">Indexing</th>
                <th className="text-right">Search</th>
                <th className="text-right">Total</th>
                <th className="text-right">AI calls</th>
                <th className="text-right pr-2">Bill</th>
              </tr>
            </thead>
            <tbody>
              {months.map(m => (
                <tr key={m.month} className="border-b border-white/5 hover:bg-white/5 transition">
                  <td className="py-2.5 pl-2 font-semibold">
                    {m.month}{m.month === b.this_month &&
                      <span className="ml-2 text-[10px] bg-emerald-500/20 text-emerald-300 rounded-full px-2 py-0.5">current — still counting</span>}
                  </td>
                  <td className="text-right text-cyan-300">{fmtMoney(m.ingest_cost)}</td>
                  <td className="text-right text-violet-300">{fmtMoney(m.search_cost)}</td>
                  <td className="text-right font-bold text-emerald-400">{fmtMoney(m.total_cost)}</td>
                  <td className="text-right text-slate-400">{m.ingest_calls + m.search_calls}</td>
                  <td className="text-right pr-2">
                    <a href={`${API}/billing/pdf?month=${m.month}`}
                       className="inline-block text-xs rounded-lg bg-indigo-500/20 text-indigo-300 px-3 py-1.5 hover:bg-indigo-500/30 transition">
                      📄 Download PDF
                    </a>
                  </td>
                </tr>
              ))}
              {months.length === 0 && (
                <tr><td colSpan="6" className="text-slate-500 text-sm py-6 text-center">
                  No billing records yet — run an indexing or a search and the first record appears.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="🏃 Indexing run history (proof of work — stored in the database)" className="mb-4">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-400 text-xs border-b border-white/10">
                <th className="text-left py-2 pl-2">Finished</th>
                <th className="text-right">Products</th>
                <th className="text-right">Failed</th>
                <th className="text-right">Tokens</th>
                <th className="text-right">Time</th>
                <th className="text-right pr-2">Cost</th>
              </tr>
            </thead>
            <tbody>
              {(b.runs || []).map((r, i) => (
                <tr key={i} className="border-b border-white/5">
                  <td className="py-2 pl-2 text-slate-300">{(r.finished_at || '').replace('T', ' ').slice(0, 16)}</td>
                  <td className="text-right text-cyan-300">{r.indexed}</td>
                  <td className="text-right text-slate-400">{r.failed}</td>
                  <td className="text-right text-slate-400">{r.tokens}</td>
                  <td className="text-right text-violet-300">{Math.round(r.elapsed_sec)}s</td>
                  <td className="text-right pr-2 font-semibold text-emerald-400">{fmtMoney(r.cost)}</td>
                </tr>
              ))}
              {(!b.runs || b.runs.length === 0) && (
                <tr><td colSpan="6" className="text-slate-500 text-sm py-4 text-center">No completed runs archived yet — the next indexing run will appear here.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="📅 Recent days (daily records in the database)">
        <div className="grid grid-cols-2 md:grid-cols-7 gap-2">
          {(b.recent_days || []).map(d => (
            <div key={d.date} className="rounded-xl bg-white/5 border border-white/10 p-2.5 text-center">
              <div className="text-[11px] text-slate-400">{d.date}</div>
              <div className="text-sm font-bold text-emerald-400 mt-0.5">{fmtMoney(d.total_cost)}</div>
              <div className="text-[10px] text-slate-500">{d.ingest_calls + d.search_calls} calls</div>
            </div>
          ))}
          {(!b.recent_days || b.recent_days.length === 0) &&
            <div className="text-slate-500 text-sm col-span-full">No daily records yet.</div>}
        </div>
      </Panel>
    </div>
  )
}

// one line inside the "total cost of ownership" box
function Row({ label, value, sub, color }) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-sm text-slate-300">{label}
        {sub && <span className="ml-2 text-[10px] text-slate-500">{sub}</span>}
      </span>
      <span className={`font-semibold ${color}`}>{value}</span>
    </div>
  )
}
