// =====================================================================
// 🖼️ PRODUCTS — browse the indexed catalogue (all ~330k), with the same
// fuzzy search the shoppers get. Read-only window into OpenSearch.
// =====================================================================
import { useEffect, useRef, useState } from 'react'
import { getProducts } from '../api.js'
import { PageTitle, Badge, Skeleton, fmtRev } from '../ui.jsx'

const pickImage = (p) =>
  p.image || p.image_url || p.thumbnail || p.thumbnail_url ||
  (Array.isArray(p.images) ? (p.images[0]?.url_thumbnail || p.images[0]?.url ||
                              p.images[0]) : null) || null

const pickPrice = (p) => {
  const v = p.calculated_price ?? p.sale_price ?? p.price ?? null
  return v != null && Number(v) > 0 ? Number(v) : null
}

export default function ProductsPage() {
  const [qq, setQq] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [err, setErr] = useState('')
  const timer = useRef(null)

  useEffect(() => {
    let dead = false
    setData(null)
    getProducts(qq, page, 24)
      .then(d => { if (!dead) { setData(d); setErr('') } })
      .catch(ex => { if (!dead) setErr(String(ex.message || ex)) })
    return () => { dead = true }
  }, [qq, page])

  const onType = (v) => {
    clearTimeout(timer.current)
    timer.current = setTimeout(() => { setPage(1); setQq(v) }, 350)
  }

  const pages = data ? Math.max(1, Math.ceil((data.total || 0) / 24)) : 1

  return (
    <div>
      <PageTitle icon="🖼️" title="Products"
                 desc="Your indexed catalogue — searched the same way shoppers search it." />

      <div className="flex items-center gap-3 mb-4">
        <input onChange={e => onType(e.target.value)}
               placeholder="search the catalogue… (fuzzy, like the shop)"
               className="flex-1 rounded-xl bg-black/25 border border-white/15 px-4 py-2.5
                          text-sm outline-none focus:border-mint/60 transition" />
        {data && <Badge tone="mint">
          {Number(data.total || 0).toLocaleString()} products</Badge>}
      </div>

      {err && <div className="text-coral text-sm mb-3">⚠️ {err}</div>}
      {!data && !err && (
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
          {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} h={150} />)}
        </div>
      )}

      {data && (data.items || []).length === 0 && (
        <div className="text-xs text-mist py-10 text-center">
          Nothing found{qq ? <> for “{qq}”</> : null} — try another word.
        </div>
      )}

      {data && (
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
          {(data.items || []).map(p => {
            const img = pickImage(p)
            const price = pickPrice(p)
            return (
              <div key={p._id} className="bg-tide border border-white/10 rounded-card
                   overflow-hidden card-in hover:border-mint/40 transition">
                <div className="h-28 bg-white/[0.04] flex items-center justify-center
                                overflow-hidden">
                  {img
                    ? <img src={img} alt="" loading="lazy"
                           className="w-full h-full object-cover" />
                    : <span className="text-3xl opacity-40">🛍️</span>}
                </div>
                <div className="p-3">
                  <div className="text-sm font-semibold leading-snug line-clamp-2 min-h-[2.4em]">
                    {p.name || p.title || `#${p._id}`}</div>
                  <div className="flex items-center justify-between mt-1.5">
                    <span className="text-[11px] text-mist truncate pr-2">
                      {p.brand || p.brand_name || ''}</span>
                    {price != null && (
                      <span className="text-xs text-sand font-bold">{fmtRev(price)}</span>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {data && pages > 1 && (
        <div className="flex items-center justify-center gap-3 mt-5">
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                  className="text-xs px-4 py-2 rounded-xl bg-white/5 border border-white/10
                             text-mist hover:bg-white/10 transition disabled:opacity-30">
            ← Prev</button>
          <span className="text-xs text-mist">page {page} of
            {' '}{Math.min(pages, 500).toLocaleString()}</span>
          <button disabled={page >= pages || page >= 500}
                  onClick={() => setPage(p => p + 1)}
                  className="text-xs px-4 py-2 rounded-xl bg-white/5 border border-white/10
                             text-mist hover:bg-white/10 transition disabled:opacity-30">
            Next →</button>
        </div>
      )}
    </div>
  )
}
