// =====================================================================
// 🔄 DATA SYNC — their field registration + every sync run, with
// copy-ready commands for their developer.
// =====================================================================
import { useEffect, useState } from 'react'
import { getSync, getClient } from '../api.js'
import { Panel, PageTitle, Badge, Skeleton, ago, TT, Stat, fmtMoney } from '../ui.jsx'
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid,
  PieChart, Pie, Cell, ComposedChart, Area, Line, Legend,
} from 'recharts'

// 🧭 what JOB each field does for the AI — grouped, not 24 meaningless slices
const FIELD_FAMILIES = [
  { key: 'identity', label: '🏷️ Identity', color: '#6d4aff',
    match: ['id', 'sku', 'name', 'barcode', 'mpn'] },
  { key: 'meaning', label: '🧠 AI meaning', color: '#5b3bd6',
    match: ['description', 'category', 'brand', 'attribute', 'color', 'size',
            'tag', 'material', 'ram', 'model', 'type', 'style', 'storage'] },
  { key: 'money', label: '💰 Money', color: '#e0821f',
    match: ['price', 'cost', 'discount', 'msrp'] },
  { key: 'stock', label: '📦 Stock', color: '#9b7bff',
    match: ['stock', 'inventory', 'quantity', 'weight', 'availab'] },
  { key: 'media', label: '🖼️ Media & links', color: '#a29ec4',
    match: ['image', 'url', 'video', 'thumb'] },
  { key: 'ops', label: '⚙️ Operations', color: '#dd5c46', match: [] },  // the rest
]

function groupFields(names) {
  const groups = FIELD_FAMILIES.map(f => ({ ...f, fields: [] }))
  for (const n of names || []) {
    const low = String(n).toLowerCase()
    const hit = groups.find(g => g.match.some(m => low.includes(m)))
    ;(hit || groups[groups.length - 1]).fields.push(n)
  }
  return groups.filter(g => g.fields.length)
}

export default function SyncPage() {
  const [d, setD] = useState(null)
  const [copied, setCopied] = useState('')
  useEffect(() => {
    let alive = true
    getSync().then(x => alive && setD(x)).catch(() => {})
    return () => { alive = false }
  }, [])

  const copy = (text, label) => {
    navigator.clipboard?.writeText(text)
    setCopied(label); setTimeout(() => setCopied(''), 1600)
  }
  const reg = d?.registration
  const last = (d?.runs || [])[0]

  return (
    <div>
      <PageTitle icon="🔄" title="Data sync"
                 desc="How your products flow into the AI search — registration, history, and the commands your developer needs." />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <Panel title="🗂️ Your registered fields — what they tell the AI">
          {d === null ? <Skeleton h={120} /> : reg ? (() => {
            const groups = groupFields(reg.field_names)
            return (
              <div className="flex flex-col items-stretch sm:flex-row sm:items-center gap-4">
                <div className="w-44 h-44 shrink-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={groups.map(g => ({ name: g.label, value: g.fields.length,
                                                    fields: g.fields.join(', ') }))}
                           dataKey="value" nameKey="name" innerRadius="55%" outerRadius="88%"
                           paddingAngle={3} isAnimationActive={false}>
                        {groups.map(g => <Cell key={g.key} fill={g.color} stroke="#ffffff" />)}
                      </Pie>
                      <Tooltip {...TT} formatter={(v, n, p) =>
                        [`${v} fields — ${p.payload.fields}`, n]} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex-1 min-w-0 w-full sm:w-auto">
                  <div className="text-sm mb-2">
                    <Badge tone="mint">{reg.field_count} fields registered</Badge>
                  </div>
                  <div className="space-y-1.5">
                    {groups.map(g => (
                      <div key={g.key} className="flex items-start gap-2 text-[11px]">
                        <span className="w-2 h-2 rounded-full mt-1 shrink-0"
                              style={{ background: g.color }} />
                        <span className="text-foam font-semibold whitespace-nowrap">
                          {g.label} ({g.fields.length})</span>
                        <span className="text-mist font-mono truncate min-w-0 flex-1">
                          {g.fields.slice(0, 4).join(', ')}{g.fields.length > 4 ? '…' : ''}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )
          })() : <div className="text-sm text-mist py-3">
                no fields registered yet — run step 1 below</div>}
        </Panel>

        <Panel title="⏱️ Last sync">
          {d === null ? <Skeleton h={120} /> : last ? (
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-mint pulse-dot" />
                {last.indexed} products indexed · {last.failed || 0} failed
              </div>
              <div className="text-xs text-mist">finished {ago(last.finished_at)} ·
                took {Math.round(last.elapsed_sec || 0)}s ·
                AI cost {fmtMoney(last.cost)}</div>
            </div>
          ) : <div className="text-sm text-mist py-3">no sync yet</div>}
        </Panel>
      </div>

      <Panel title="🔗 Your BigCommerce store is connected directly">
        <div className="space-y-3 text-sm">
          {[
            ['Products flow in automatically',
             'BigCommerce catalogue  →  AI reads each product  →  instantly searchable'],
            ['Need a re-sync or a new source?',
             'Ask on the Support page (or tell blu) — our team runs syncs for you'],
          ].map(([label, cmd]) => (
            <div key={label}>
              <div className="text-xs text-mist mb-1">{label}</div>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-[12px] bg-black/25 border border-white/10
                                 rounded-lg px-3 py-2 overflow-x-auto whitespace-nowrap">{cmd}</code>
                <button onClick={() => copy(cmd, label)}
                        className="text-xs px-3 py-2 rounded-lg bg-mint/20 border border-mint/40
                                   text-mint hover:bg-mint/30 transition whitespace-nowrap">
                  {copied === label ? '✓ copied' : 'copy'}</button>
              </div>
            </div>
          ))}
          <div className="text-[11px] text-mist">
            🔐 Your API key was shown once when your account was created — it is never
            displayed here. Lost it? Ask your provider to rotate it.
          </div>
        </div>
      </Panel>

      <div className="mt-4">
        <Panel title="📜 Sync history">
          {d === null ? <Skeleton h={100} /> : (d.runs || []).length ? (
            <div className="space-y-2">
              {(d.runs || []).map((r, i) => (
                <div key={i} className="flex items-center justify-between text-sm rounded-lg
                     px-3 py-2 bg-white/[0.03] border border-white/5">
                  <span className="text-xs">{(r.finished_at || '').replace('T', ' ').slice(0, 16)}</span>
                  <span className="text-xs text-mist">{r.indexed} products ·{' '}
                    {Math.round(r.elapsed_sec || 0)}s · {fmtMoney(r.cost)}</span>
                </div>
              ))}
            </div>
          ) : <div className="text-sm text-mist py-3">nothing yet</div>}
        </Panel>
      </div>

      {/* ⚙️ the indexing story — same numbers the engine room sees */}
      {(() => {
        const runs = [...(d?.runs || [])]
          .sort((a, b) => String(a.finished_at || '').localeCompare(String(b.finished_at || '')))
        const latest = runs[runs.length - 1]
        const totalCost = runs.reduce((s, r) => s + (Number(r.cost) || 0), 0)
        const totalTokens = runs.reduce((s, r) => s + (Number(r.tokens) || 0), 0)
        const el = Number(latest?.elapsed_sec) || 0
        const idx = Number(latest?.indexed) || 0
        const speed = el > 1 ? Math.round((idx / el) * 60 * 10) / 10 : 0
        const avgMs = idx ? Math.round((el * 1000) / idx * 10) / 10 : 0
        const fmtT = (sec) => sec >= 60
          ? `${Math.floor(sec / 60)}m ${Math.round(sec % 60)}s` : `${Math.round(sec)}s`
        let cum = 0, cost = 0
        const timeline = [{ label: 'start', indexed: 0, cost: 0 },
          ...runs.map(r => {
            cum += Number(r.indexed) || 0
            cost = Math.round((cost + (Number(r.cost) || 0)) * 1e6) / 1e6
            return { label: String(r.finished_at || '').slice(5, 16).replace('T', ' '),
                     indexed: cum, cost }
          })]
        return (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
              <Stat label="Indexed" value={idx} sub={latest ? '100% complete' : 'no sync yet'}
                    accent="text-mint" />
              <Stat label="Total AI cost" value={fmtMoney(totalCost)}
                    sub={`${totalTokens.toLocaleString()} tokens`} accent="text-teal"
                    animate={false} />
              <Stat label="Speed" value={speed ? `${speed}/min` : '—'}
                    sub={avgMs ? `avg ${avgMs} ms each` : 'per product'}
                    accent="text-foam" animate={false} />
              <Stat label="Indexing time" value={latest ? fmtT(el) : '—'}
                    sub={`success 100% · ${latest?.failed || 0} failed`}
                    accent="text-sand" animate={false} />
            </div>

            <Panel title="📈 Indexed count & cost over time" className="h-72 mt-4">
              {d === null ? <Skeleton h={160} /> : runs.length ? (
                <ResponsiveContainer width="100%" height="84%">
                  <ComposedChart data={timeline}
                                 margin={{ top: 6, right: 6, left: -12, bottom: 0 }}>
                    <defs>
                      <linearGradient id="gIdx" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#6d4aff" stopOpacity={0.4} />
                        <stop offset="100%" stopColor="#6d4aff" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid vertical={false} />
                    <XAxis dataKey="label" tickLine={false} axisLine={false} minTickGap={24} />
                    <YAxis yAxisId="l" allowDecimals={false} tickLine={false}
                           axisLine={false} width={44} />
                    <YAxis yAxisId="r" orientation="right" tickLine={false} axisLine={false}
                           width={64} tick={false} />
                    <Tooltip {...TT} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Area yAxisId="l" type="linear" dataKey="indexed"
                          name="products indexed" stroke="#6d4aff" strokeWidth={2.5}
                          fill="url(#gIdx)" isAnimationActive={false} />
                    <Line yAxisId="r" type="linear" dataKey="cost" name="cost ($)"
                          stroke="#e0821f" strokeWidth={2} dot={{ r: 3 }}
                          isAnimationActive={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              ) : <div className="h-full flex items-center justify-center text-sm text-mist">
                    the line starts drawing on your first sync</div>}
            </Panel>
          </>
        )
      })()}

      {/* 🛤️ how the pipeline works — animated, simple */}
      <Panel title="🛤️ How your products travel into the AI" className="mt-4">
        <div className="flex flex-col lg:flex-row items-stretch gap-3">
          {[['🏬', 'Your store', 'products live in your shop system'],
            ['📮', 'One API call', 'your developer POSTs them to us'],
            ['🧠', 'AI reads each one', 'meaning is embedded, not just words'],
            ['🔎', 'Instantly searchable', 'shoppers find them the human way']]
            .map(([ic, t, sub], i) => (
            <div key={t} className="flex-1 flex items-center gap-3">
              <div className="flex-1 rounded-xl border border-mint/20 bg-mint/5 p-4
                   text-center tilt-3d">
                <div className="text-3xl mb-1 blu-float" style={{ animationDelay: `${i * 0.4}s` }}>{ic}</div>
                <div className="text-sm font-bold text-foam">{t}</div>
                <div className="text-[11px] text-mist mt-1">{sub}</div>
              </div>
              {i < 3 && <div className="hidden lg:block text-mint text-xl pulse-dot"
                             style={{ animationDelay: `${i * 0.3}s` }}>→</div>}
            </div>
          ))}
        </div>
      </Panel>

      {/* 📦 products per sync — the pipeline's heartbeat over time */}
      <Panel title="📦 Products indexed per sync" className="h-64 mt-4">
        {d === null ? <Skeleton h={160} /> : (d.runs || []).length ? (
          <ResponsiveContainer width="100%" height="84%">
            <BarChart data={[...(d.runs || [])].slice(0, 15).reverse().map(r => ({
                        date: (r.finished_at || '').slice(5, 16).replace('T', ' '),
                        products: r.indexed || 0, failed: r.failed || 0 }))}
                      margin={{ top: 6, right: 8, left: -8, bottom: 0 }}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="date" tickLine={false} axisLine={false} minTickGap={22} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={44}
                     tickFormatter={v => v >= 1000 ? `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k` : v} />
              <Tooltip {...TT} />
              <Bar dataKey="products" name="products indexed" fill="#5b3bd6"
                   radius={[5, 5, 0, 0]} isAnimationActive={false} />
              <Bar dataKey="failed" name="failed" fill="#dd5c46"
                   radius={[5, 5, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        ) : <div className="h-full flex items-center justify-center text-sm text-mist">
              your first sync draws the first bar</div>}
      </Panel>
    </div>
  )
}
