// Overview page — the main summary
import {
  ComposedChart, Area, Line, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from 'recharts'
import Sphere3D from '../Sphere3D.jsx'
import { Card, Stat, PageTitle, Panel, TT, fmtTime, fmtMoney } from '../ui.jsx'

export default function Overview({ stats, osInfo, fields, goTo }) {
  const s = stats || {}
  const os = osInfo || {}
  const f = fields || {}
  const timeline = s.timeline || []

  return (
    <div>
      <PageTitle icon="📊" title="Overview" desc="Live view of products flowing into OpenSearch" />

      {/* 3D + key stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <Card className="h-60 md:h-72 relative overflow-hidden">
          <Sphere3D progress={s.progress_pct || 0} active={(s.source_total || 0) > 0 && (s.indexed || 0) < (s.source_total || 0)} />
          <div className="absolute top-3 left-4 text-xs text-slate-400 max-w-[85%] leading-snug">
            3D search index — each dot is a product; the glowing core grows and turns green as indexing completes.
          </div>
          <div className="absolute bottom-3 left-4">
            <div className="text-3xl font-bold text-cyan-300">{s.indexed || 0}</div>
            <div className="text-xs text-slate-400">of {s.source_total || 0} products</div>
          </div>
        </Card>

        <div className="lg:col-span-2 grid grid-cols-1 xs:grid-cols-2 gap-4">
          <Stat label="Indexed" value={`${s.indexed || 0} / ${s.source_total || 0}`} sub={`${s.progress_pct || 0}% complete`} accent="text-cyan-400" />
          <Stat label="Total AI Cost" value={fmtMoney(s.ai?.total_cost)} sub={`${s.ai?.total_calls || 0} AI calls`} accent="text-emerald-400" />
          <Stat label="Speed" value={`${s.speed_per_min || 0}/min`} sub={`avg ${s.avg_embed_ms || 0} ms each`} />
          <Stat label="Indexing Time" value={fmtTime(s.elapsed_sec)} sub={`success ${s.success_rate ?? 100}% · ${s.failed || 0} failed`} accent="text-violet-400" />
          <div className="xs:col-span-2">
            <Card className="p-4">
              <div className="flex flex-wrap justify-between items-center gap-2 text-xs text-slate-400 mb-2">
                <span>Progress</span>
                {/* live numbers straight from the database — same sources as the OpenSearch / Fields pages */}
                <span className="flex items-center gap-2">
                  <button onClick={() => goTo('opensearch')}
                          className="px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 font-semibold hover:bg-cyan-500/20 transition">
                    🗄️ In database: {(os.docs ?? 0).toLocaleString()} products
                  </button>
                  <button onClick={() => goTo('fields')}
                          className="px-2 py-0.5 rounded-full bg-violet-500/10 border border-violet-500/30 text-violet-300 font-semibold hover:bg-violet-500/20 transition">
                    🗂️ Fields: {f.registered ? f.field_count ?? (f.fields || []).length : 0} registered
                  </button>
                </span>
                <span className="hidden sm:inline">{s.model || 'text-embedding-3-large'}</span>
              </div>
              <div className="h-3 rounded-full bg-white/10 overflow-hidden">
                <div className="h-full bg-gradient-to-r from-cyan-400 to-emerald-400 transition-all duration-700"
                     style={{ width: `${s.progress_pct || 0}%` }} />
              </div>
            </Card>
          </div>
        </div>
      </div>

      {/* 2-line graph WITH legend */}
      <Panel title="📈 Indexed count & cost over time" className="h-64 md:h-80 mb-4">
        {timeline.length === 0 ? (
          <div className="h-[86%] flex items-center justify-center text-sm text-slate-400">
            no indexing history recorded yet — the line starts drawing on this
            client's next sync
          </div>
        ) : (
        <ResponsiveContainer width="100%" height="86%">
          <ComposedChart data={timeline} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="gi" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.45} />
                <stop offset="100%" stopColor="#38bdf8" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
            <XAxis dataKey={timeline[0]?.date ? 'date' : 't'} stroke="#64748b"
                   tick={{ fontSize: 11 }} unit={timeline[0]?.date ? '' : 's'}
                   tickFormatter={v => timeline[0]?.date ? String(v).slice(5) : v}
                   minTickGap={22} />
            <YAxis yAxisId="l" stroke="#38bdf8" tick={{ fontSize: 11 }} allowDecimals={false} />
            <YAxis yAxisId="r" orientation="right" stroke="#34d399" tick={{ fontSize: 10 }} width={64}
                   tickFormatter={fmtMoney} />
            <Tooltip {...TT} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Area isAnimationActive={false} yAxisId="l" type="linear" dataKey="indexed" name="Products indexed (count)" stroke="#38bdf8" strokeWidth={2.5} fill="url(#gi)"  />
            <Line isAnimationActive={false} yAxisId="r" type="linear" dataKey="cost" name="Cost ($)" stroke="#34d399" strokeWidth={2} dot={false}  />
          </ComposedChart>
        </ResponsiveContainer>
        )}
      </Panel>

      {/* nav tiles to detail pages */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <NavTile icon="🔍" title="OpenSearch" desc="index size, shards, docs + charts" onClick={() => goTo('opensearch')} />
        <NavTile icon="🔌" title="API" desc="endpoints & request traffic" onClick={() => goTo('api')} />
        <NavTile icon="🤖" title="AI / OpenAI" desc="cost breakdown & monitoring" onClick={() => goTo('ai')} />
      </div>
    </div>
  )
}

function NavTile({ icon, title, desc, onClick }) {
  return (
    <button onClick={onClick}
            className="text-left rounded-2xl bg-white/5 border border-white/10 p-4 hover:border-cyan-400/40 hover:bg-white/10 transition">
      <div className="text-lg">{icon} <span className="font-semibold">{title}</span></div>
      <div className="text-xs text-slate-400 mt-1">{desc} →</div>
    </button>
  )
}
