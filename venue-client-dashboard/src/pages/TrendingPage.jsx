// =====================================================================
// 🔥 TRENDING — the products shoppers love right now, ranked by the
// backend's own trending score (clicks + carts + purchases, time-decayed).
// =====================================================================
import { useEffect, useState } from 'react'
import { getTrending } from '../api.js'
import { Panel, PageTitle, Badge, Skeleton } from '../ui.jsx'

export default function TrendingPage() {
  const [rows, setRows] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    let dead = false
    getTrending()
      .then(d => { if (!dead) setRows(d.trending || []) })
      .catch(ex => { if (!dead) setErr(String(ex.message || ex)) })
    return () => { dead = true }
  }, [])

  if (err) return <div className="text-coral text-sm">⚠️ {err}</div>

  const max = Math.max(1, ...(rows || []).map(r => r.score || 0))

  return (
    <div>
      <PageTitle icon="🔥" title="Trending products"
                 desc="What shoppers are clicking, carting and buying — right now." />

      {!rows && <div className="space-y-2">
        <Skeleton h={64} /><Skeleton h={64} /><Skeleton h={64} /></div>}

      {rows && (
        <Panel title="🏆 Top 10 by trending score"
               right={<Badge tone="sand">live from shopper events</Badge>}>
          {rows.length === 0 && (
            <div className="text-xs text-mist py-8 text-center">
              No trending data yet — it builds up as shoppers click products.
            </div>
          )}
          <div className="space-y-2">
            {rows.map((r, i) => (
              <div key={r.product_id} className="rounded-xl px-3 py-2.5
                   bg-white/[0.03] border border-white/5">
                <div className="flex items-center gap-3">
                  <span className={`w-7 h-7 rounded-full flex items-center justify-center
                        text-xs font-extrabold shrink-0 ${
                          i === 0 ? 'bg-sand/25 text-sand' :
                          i === 1 ? 'bg-mint/20 text-mint' :
                          'bg-white/5 text-mist'}`}>{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold truncate">{r.name}</div>
                    <div className="text-[11px] text-mist">#{r.product_id}</div>
                  </div>
                  <div className="text-right text-[11px] text-mist shrink-0">
                    <span className="text-mint">{r.clicks} 🔎</span>
                    {'  '}<span className="text-teal">{r.carts} 🛒</span>
                    {'  '}<span className="text-sand">{r.purchases} 💰</span>
                  </div>
                </div>
                {/* score bar */}
                <div className="mt-2 h-1.5 rounded-full bg-white/5 overflow-hidden">
                  <div className="h-full rounded-full bg-gradient-to-r from-mint to-sand"
                       style={{ width: `${Math.max(4, (r.score / max) * 100)}%` }} />
                </div>
              </div>
            ))}
          </div>
          <div className="text-[11px] text-mist mt-3">
            The same scores power the shop's own “Trending” row — what you see
            here is exactly what shoppers are shown.
          </div>
        </Panel>
      )}
    </div>
  )
}
