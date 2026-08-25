// =====================================================================
// 🖼️ PRODUCTS — their live catalogue: search, category filter, CSV export
// =====================================================================
import { useEffect, useRef, useState } from 'react'
import { getProducts } from '../api.js'
import { Panel, PageTitle, Badge, Skeleton } from '../ui.jsx'

export default function ProductsPage() {
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const [page, setPage] = useState(1)
  const [d, setD] = useState(null)
  const timer = useRef(null)

  const load = (qq = q, cat = category, pg = page) =>
    getProducts(qq, cat, pg, 24).then(setD).catch(() => setD({ total: 0, items: [], categories: [] }))

  useEffect(() => { load() }, [])
  const onType = (v) => {
    setQ(v); setPage(1)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => load(v, category, 1), 350)
  }
  const pickCat = (c) => {
    const next = category === c ? '' : c
    setCategory(next); setPage(1); load(q, next, 1)
  }
  const go = (pg) => { setPage(pg); load(q, category, pg) }

  const exportCsv = () => {
    const rows = d?.items || []
    const esc = v => `"${String(v ?? '').replace(/"/g, '""')}"`
    const csv = ['ID,Name,Category,Brand,Price']
      .concat(rows.map(r => [r.id, r.name, r.category, r.brand, r.price].map(esc).join(',')))
      .join('\n')
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `products-page${page}.csv`
    a.click(); URL.revokeObjectURL(a.href)
  }

  const pages = d ? Math.max(1, Math.ceil((d.total || 0) / 24)) : 1

  return (
    <div>
      <PageTitle icon="🖼️" title="Your products"
                 desc="Everything in your AI search index, exactly as shoppers can find it." />

      <div className="flex gap-3 flex-wrap items-center mb-4">
        <input value={q} onChange={e => onType(e.target.value)}
               placeholder="Search your catalogue…"
               className="flex-1 min-w-[220px] max-w-md rounded-xl bg-tide border
                          border-white/15 px-3 py-2.5 text-sm outline-none
                          focus:border-mint/60 transition" />
        <Badge tone="mint">{d ? `${(d.total || 0).toLocaleString()} products` : '…'}</Badge>
        <button onClick={exportCsv} disabled={!d?.items?.length}
                className="text-xs px-3 py-2 rounded-lg bg-mint/20 border border-mint/40
                           text-mint hover:bg-mint/30 transition disabled:opacity-40 font-semibold">
          ⬇️ Excel (this page)</button>
      </div>

      {d?.categories?.length > 0 && (
        <div className="flex gap-2 flex-wrap mb-4">
          {d.categories.slice(0, 12).map(c => (
            <button key={c.value} onClick={() => pickCat(c.value)}
                    className={`text-xs px-3 py-2.5 md:py-1.5 rounded-full border transition ${
                      category === c.value
                        ? 'bg-mint/25 border-mint/50 text-foam'
                        : 'bg-white/5 border-white/10 text-mist hover:bg-white/10'}`}>
              {c.value} <span className="opacity-60">({c.count})</span>
            </button>
          ))}
        </div>
      )}

      {d === null ? (
        <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-4">
          {Array.from({ length: 12 }).map((_, i) => <Skeleton key={i} h={180} />)}
        </div>
      ) : d.items.length ? (
        <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-4">
          {d.items.map((p, i) => (
            <div key={`${p.id}-${i}`}
                 className="bg-tide border border-white/10 rounded-card overflow-hidden tilt-3d card-in">
              <div className="h-32 bg-black/25 flex items-center justify-center overflow-hidden">
                {p.image ? <img src={p.image} loading="lazy" alt=""
                                className="w-full h-full object-cover" />
                         : <span className="text-3xl">🛍️</span>}
              </div>
              <div className="p-3">
                <div className="text-[13px] font-semibold leading-tight h-9 line-clamp-2">
                  {p.name}</div>
                <div className="text-[11px] text-mist mt-1 truncate">
                  {[p.brand, p.category].filter(Boolean).join(' · ')}</div>
                {p.price != null &&
                  <div className="text-sm font-extrabold text-mint mt-1">
                    ${Number(p.price).toFixed(2)}</div>}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <Panel><div className="text-sm text-mist py-4">
          nothing matches — try clearing the search or filter</div></Panel>
      )}

      {pages > 1 && (
        <div className="flex items-center justify-center gap-3 mt-5 text-sm">
          <button disabled={page <= 1} onClick={() => go(page - 1)}
                  className="px-3 py-2.5 md:py-1.5 rounded-lg bg-white/5 border border-white/10
                             disabled:opacity-30 hover:bg-white/10 transition">← prev</button>
          <span className="text-mist text-xs">page {page} of {pages}</span>
          <button disabled={page >= pages} onClick={() => go(page + 1)}
                  className="px-3 py-2.5 md:py-1.5 rounded-lg bg-white/5 border border-white/10
                             disabled:opacity-30 hover:bg-white/10 transition">next →</button>
        </div>
      )}
    </div>
  )
}
