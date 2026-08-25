// =====================================================================
// 🛰️ LIVE ACTIVITY — the shopper event stream, refreshing itself.
// Filter chips narrow to one event type; counts show the all-time mix.
// =====================================================================
import { useEffect, useState } from 'react'
import { getEvents } from '../api.js'
import { Panel, PageTitle, Badge, Skeleton, fmtRev, ago } from '../ui.jsx'

const TYPES = [
  { id: 'all',         label: 'All',        icon: '🌐' },
  { id: 'click',       label: 'Clicks',     icon: '🔎' },
  { id: 'add_to_cart', label: 'Carts',      icon: '🛒' },
  { id: 'purchase',    label: 'Purchases',  icon: '💰' },
  { id: 'wishlist',    label: 'Wishlist',   icon: '💜' },
  { id: 'impression',  label: 'Impressions', icon: '👀' },
]

const ICON = { click: '🔎', add_to_cart: '🛒', purchase: '💰',
               wishlist: '💜', impression: '👀', view: '👁️', search: '⌨️' }

export default function ActivityPage() {
  const [type, setType] = useState('all')
  const [data, setData] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    let dead = false
    const load = () => getEvents(type, 60)
      .then(d => { if (!dead) { setData(d); setErr('') } })
      .catch(ex => { if (!dead) setErr(String(ex.message || ex)) })
    setData(null); load()
    const t = setInterval(load, 10000)
    return () => { dead = true; clearInterval(t) }
  }, [type])

  return (
    <div>
      <PageTitle icon="🛰️" title="Live activity"
                 desc="Every shopper event as it happens — refreshes every 10 seconds." />

      {/* filter chips + all-time counts */}
      <div className="flex flex-wrap gap-2 mb-4">
        {TYPES.map(t => (
          <button key={t.id} onClick={() => setType(t.id)}
                  className={`text-xs px-3 py-1.5 rounded-full border transition ${
                    type === t.id
                      ? 'bg-mint text-white border-mint font-bold'
                      : 'bg-white/5 text-mist border-white/10 hover:bg-white/10'}`}>
            {t.icon} {t.label}
            {t.id !== 'all' && data?.counts?.[t.id] != null && (
              <span className="ml-1 opacity-75">
                {Number(data.counts[t.id]).toLocaleString()}</span>
            )}
          </button>
        ))}
      </div>

      {err && <div className="text-coral text-sm mb-3">⚠️ {err}</div>}
      {!data && !err && <div className="space-y-2">
        <Skeleton h={54} /><Skeleton h={54} /><Skeleton h={54} /></div>}

      {data && (
        <Panel title="📡 Latest events"
               right={<Badge tone="mint">newest first</Badge>}>
          {(data.recent || []).length === 0 && (
            <div className="text-xs text-mist py-8 text-center">
              Nothing here yet — events arrive when shoppers use the search.
            </div>
          )}
          <div className="space-y-1.5">
            {(data.recent || []).map((e, i) => (
              <div key={i} className="flex items-center gap-3 rounded-lg px-3 py-2
                   bg-white/[0.03] border border-white/5 text-sm">
                <span>{ICON[e.type] || '•'}</span>
                <span className="capitalize text-xs text-mist w-20 shrink-0">
                  {e.type.replace(/_/g, ' ')}</span>
                <span className="flex-1 truncate">
                  {e.query ? <>“{e.query}”</> : null}
                  {e.query && e.product_id ? ' → ' : null}
                  {e.product_id ? <span className="text-mist">#{e.product_id}</span> : null}
                  {!e.query && !e.product_id ? <span className="text-mist">—</span> : null}
                </span>
                {e.value > 0 && (
                  <span className="text-xs text-sand">{fmtRev(e.value)}</span>
                )}
                <span className="text-[11px] text-mist shrink-0">{ago(e.at)}</span>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  )
}
