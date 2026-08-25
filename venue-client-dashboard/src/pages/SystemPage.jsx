// =====================================================================
// 🖥️ SYSTEM (admin only) — the machine room: indexing progress, every
// service's pulse, disk + memory. Polls every 10 seconds. Read-only.
// =====================================================================
import { useEffect, useState } from 'react'
import { getSystem } from '../api.js'
import { Panel, PageTitle, Badge, Skeleton } from '../ui.jsx'

function Bar({ pct, tone = 'mint' }) {
  const color = tone === 'sand' ? '#e0821f' : tone === 'coral' ? '#e05252' : '#6d4aff'
  return (
    <div className="h-3 rounded-full bg-white/5 overflow-hidden">
      <div className="h-full rounded-full transition-all duration-700"
           style={{ width: `${Math.max(2, Math.min(100, pct))}%`, background: color }} />
    </div>
  )
}

function Service({ name, up, extra }) {
  return (
    <div className={`rounded-xl px-4 py-3 border flex items-center justify-between ${
      up ? 'bg-mint/5 border-mint/25' : 'bg-coral/10 border-coral/40'}`}>
      <span className="text-sm font-semibold flex items-center gap-2">
        <span className={`w-2.5 h-2.5 rounded-full ${up ? 'bg-mint pulse-dot' : 'bg-coral'}`} />
        {name}
      </span>
      <span className={`text-xs ${up ? 'text-mint' : 'text-coral'}`}>
        {up ? (extra || 'running') : 'DOWN'}</span>
    </div>
  )
}

export default function SystemPage() {
  const [s, setS] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    let dead = false
    const load = () => getSystem()
      .then(d => { if (!dead) { setS(d); setErr('') } })
      .catch(ex => { if (!dead) setErr(String(ex.message || ex)) })
    load()
    const t = setInterval(load, 10000)
    return () => { dead = true; clearInterval(t) }
  }, [])

  if (err) return <div className="text-coral text-sm">⚠️ {err}</div>
  if (!s) return <div className="space-y-3"><Skeleton h={120} /><Skeleton h={180} /></div>

  const idx = s.indexing || {}
  const done = idx.pct >= 99.5

  return (
    <div>
      <PageTitle icon="🖥️" title="System"
                 desc="The machine room — refreshes every 10 seconds. Admin eyes only." />

      <Panel title="📦 Indexing progress" className="mb-4"
             right={<Badge tone={done ? 'mint' : 'sand'}>
               {done ? '● complete' : '● running'}</Badge>}>
        <div className="flex items-end justify-between mb-2">
          <div className="text-3xl font-extrabold text-foam tabular">
            {(idx.count || 0).toLocaleString()}
            <span className="text-sm text-mist font-normal">
              {' '}/ {(idx.target || 0).toLocaleString()} products</span>
          </div>
          <div className={`text-2xl font-extrabold tabular ${done ? 'text-mint' : 'text-sand'}`}>
            {idx.pct}%</div>
        </div>
        <Bar pct={idx.pct} tone={done ? 'mint' : 'sand'} />
        <div className="text-[11px] text-mist mt-2">
          {done ? 'the full catalogue is searchable 🎉'
                : 'products become searchable the moment they are indexed — no need to wait for 100%'}
        </div>
      </Panel>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
        <Service name="🔎 Search API" up={s.search_api?.up} />
        <Service name="🗄️ OpenSearch" up={s.opensearch?.up}
                 extra={s.opensearch?.status && `cluster ${s.opensearch.status}`} />
        <Service name="🐘 Postgres (events)" up={s.postgres?.up}
                 extra={s.postgres?.up ? `${(s.postgres.events || 0).toLocaleString()} events` : null} />
        <Service name="⚡ Redis cache" up={s.redis?.up} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Panel title="💾 Disk">
          {s.disk ? (<>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-mist">{s.disk.used_gb} GB used</span>
              <span className="text-foam font-semibold">{s.disk.total_gb} GB total</span>
            </div>
            <Bar pct={s.disk.pct} tone={s.disk.pct > 85 ? 'coral' : 'mint'} />
            {s.disk.pct > 85 && <div className="text-xs text-coral mt-2">
              ⚠️ disk almost full — tell the team</div>}
          </>) : <div className="text-xs text-mist">not readable</div>}
        </Panel>
        <Panel title="🧠 Memory">
          {s.memory ? (<>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-mist">{s.memory.used_gb} GB used</span>
              <span className="text-foam font-semibold">{s.memory.total_gb} GB total</span>
            </div>
            <Bar pct={s.memory.pct} tone={s.memory.pct > 90 ? 'coral' : 'mint'} />
          </>) : <div className="text-xs text-mist">not readable</div>}
        </Panel>
      </div>

      <div className="grid grid-cols-3 gap-3 mt-4">
        {[['events', s.postgres?.events], ['orders', s.postgres?.orders],
          ['product metrics', s.postgres?.product_metrics]].map(([l, v]) => (
          <div key={l} className="bg-tide border border-white/10 rounded-card p-4 text-center">
            <div className="text-xl font-extrabold text-foam tabular">
              {(v ?? 0).toLocaleString()}</div>
            <div className="text-[11px] text-mist mt-0.5">{l}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
