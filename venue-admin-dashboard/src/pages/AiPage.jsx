// AI page — AI monitoring: cost split, tokens, cost-over-time, forecast
import {
  PieChart, Pie, Cell, BarChart, Bar, AreaChart, Area,
  ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from 'recharts'
import { Stat, PageTitle, Panel, TT, fmtMoney } from '../ui.jsx'

export default function AiPage({ stats }) {
  const s = stats || {}
  const ai = s.ai || {}
  const costSplit = [{ name: 'Indexing', value: ai.ingest_cost || 0 }, { name: 'Search', value: ai.search_cost || 0 }]
  const tokenSplit = [{ name: 'Indexing', value: ai.ingest_tokens || 0 }, { name: 'Search', value: ai.search_tokens || 0 }]
  const timeline = (s.timeline || []).map(p => ({ t: p.t, cost: p.cost }))

  return (
    <div>
      <PageTitle icon="🤖" title="AI / OpenAI" desc="Every AI call is tracked — indexing AND search both cost money." />

      <div className="grid grid-cols-1 xs:grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <Stat label="Total AI cost" value={fmtMoney(ai.total_cost)} sub={`${ai.total_calls || 0} calls`} accent="text-emerald-400" />
        <Stat label="Indexing AI" value={fmtMoney(ai.ingest_cost)} sub={`${ai.ingest_calls || 0} calls · ${ai.ingest_avg_ms || 0}ms`} accent="text-cyan-400" />
        <Stat label="Search AI" value={fmtMoney(ai.search_cost)} sub={`${ai.search_calls || 0} calls · ${ai.search_avg_ms || 0}ms`} accent="text-violet-400" />
        <Stat label="Model" value="3-large" sub={`3072 dims · $${s.rate_per_1m || 0.13}/1M tokens`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <Panel title="🍩 Cost split — indexing vs search" className="h-60 md:h-72">
          <ResponsiveContainer width="100%" height="86%">
            <PieChart>
              <Pie isAnimationActive={false} data={costSplit} dataKey="value" nameKey="name" innerRadius="55%" outerRadius="90%" paddingAngle={3} stroke="none">
                <Cell fill="#38bdf8" /><Cell fill="#a78bfa" />
              </Pie>
              <Tooltip {...TT} formatter={(v) => fmtMoney(v)} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title="📊 Tokens used — indexing vs search" className="h-60 md:h-72">
          <ResponsiveContainer width="100%" height="86%">
            <BarChart data={tokenSplit} margin={{ top: 5, right: 10, left: -12, bottom: 0 }}>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
              <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} />
              <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
              <Tooltip {...TT} />
              <Bar isAnimationActive={false} dataKey="value" name="tokens" radius={[4, 4, 0, 0]}>
                <Cell fill="#38bdf8" /><Cell fill="#a78bfa" />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Panel>
      </div>

      <Panel title="📈 Cost over time ($)" className="h-60 md:h-72 mb-4">
        <ResponsiveContainer width="100%" height="86%">
          <AreaChart data={timeline} margin={{ top: 5, right: 10, left: -4, bottom: 0 }}>
            <defs>
              <linearGradient id="gc" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#34d399" stopOpacity={0.45} />
                <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
            <XAxis dataKey="t" stroke="#64748b" tick={{ fontSize: 11 }} unit="s" />
            <YAxis stroke="#64748b" tick={{ fontSize: 10 }} width={64} tickFormatter={fmtMoney} />
            <Tooltip {...TT} />
            <Area isAnimationActive={false} type="linear" dataKey="cost" name="Cost ($)" stroke="#34d399" strokeWidth={2} fill="url(#gc)"  />
          </AreaChart>
        </ResponsiveContainer>
      </Panel>

      <Panel title="🔍 Live search queries (what people are searching right now)" className="mb-4">
        {(s.recent_searches || []).length === 0
          ? <div className="text-sm text-slate-500">No searches yet — try the /search API or the Products page search box.</div>
          : <div className="space-y-1">
              {(s.recent_searches || []).map((r, i) => (
                <div key={i} className="flex items-center justify-between text-sm rounded-lg bg-white/5 px-3 py-1.5">
                  <span className="text-slate-200 truncate">“{r.q}”</span>
                  <span className="text-xs text-slate-400 shrink-0 ml-3">{r.tokens} tokens · {r.ms} ms</span>
                </div>
              ))}
            </div>}
      </Panel>

      <Panel title="💵 Cost forecast — scaling the catalog">
        <div className="grid grid-cols-1 xs:grid-cols-2 md:grid-cols-4 gap-3">
          <Fc label="Now" value={fmtMoney(s.total_cost)} />
          <Fc label="1,000 products" value={fmtMoney(s.forecast?.["1k"])} />
          <Fc label="10,000 products" value={fmtMoney(s.forecast?.["10k"])} />
          <Fc label="100,000 products" value={fmtMoney(s.forecast?.["100k"])} />
        </div>
      </Panel>
    </div>
  )
}

function Fc({ label, value }) {
  return (
    <div className="rounded-xl bg-white/5 border border-white/10 p-3">
      <div className="text-xs text-slate-400">{label}</div>
      <div className="text-xl font-bold text-emerald-400 mt-1">{value}</div>
    </div>
  )
}
