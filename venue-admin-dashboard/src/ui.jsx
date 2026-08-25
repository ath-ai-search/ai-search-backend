// =====================================================================
// ui.jsx — shared building blocks used by every page
// =====================================================================
import { useState } from 'react'

// Azure-edition palette — blue/violet family, soft on the eyes
export const DONUT = ['#5f95ff', '#9d7bff', '#3ecfad', '#f5c04e', '#f08bb4', '#7fb3ff', '#f0876f',
                      '#45d6c8', '#b78cff', '#ffd97a', '#ff9f6e', '#6fe3a1', '#e08cf0', '#4fb7ff']

// shared hover tooltip — glass panel with glow (used by every chart)
export const TT = {
  contentStyle: {
    background: 'rgba(13, 18, 38, 0.92)',
    border: '1px solid rgba(95, 149, 255, 0.35)',
    borderRadius: 12,
    boxShadow: '0 12px 32px -8px rgba(0, 0, 0, 0.6), 0 0 20px -6px rgba(95, 149, 255, 0.35)',
    backdropFilter: 'blur(8px)',
    padding: '10px 14px',
  },
  itemStyle: { color: '#e6edfb', fontSize: 12 },
  labelStyle: { color: '#8fa3c8', fontSize: 11, marginBottom: 4 },
  cursor: { stroke: 'rgba(95, 149, 255, 0.35)', strokeWidth: 1 },
}

export const fmtTime = (sec) => {
  sec = Math.round(sec || 0)
  return sec < 60 ? `${sec}s` : `${Math.floor(sec / 60)}m ${sec % 60}s`
}

// 💵 Smart money format — short and honest:
//   0          -> $0.00
//   0.002201   -> $0.0022   (tiny: only 2 meaningful digits)
//   0.000737   -> $0.00074
//   0.61       -> $0.61
export const fmtMoney = (v) => {
  v = Number(v) || 0
  if (v === 0) return '$0.00'
  if (v >= 0.01) return '$' + v.toFixed(2)
  if (v >= 0.000001) return '$' + parseFloat(v.toPrecision(2)).toString()
  return '<$0.000001'
}
/* 📈 CHART RULE (boss): a graph must never plunge back to the floor.
   trimTail — cut the empty tail so the line doesn't dive at the right edge
             (a half-finished "today" looked like the business dying).
   accumulate — running totals, so the line only ever climbs. Quiet days in
             the MIDDLE still stay flat: that part is the true story. */
export function trimTail(rows, key = 'count') {
  const out = [...(rows || [])]
  while (out.length > 2 && !Number(out[out.length - 1]?.[key])) out.pop()
  return out
}
export function accumulate(rows, keys = ['count']) {
  const acc = Object.fromEntries(keys.map(k => [k, 0]))
  return (rows || []).map(r => {
    const out = { ...r }
    for (const k of keys) {
      acc[k] += Number(r[k]) || 0
      out[k] = Math.round(acc[k] * 1e6) / 1e6
    }
    return out
  })
}

export const fmtBytes = (b) => {
  b = b || 0
  if (b < 1024) return `${b} B`
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1048576).toFixed(2)} MB`
}
export const fmtVal = (v) => {
  if (v === null || v === undefined) return '-'
  if (typeof v === 'object') return JSON.stringify(v)
  const s = String(v)
  return s.length > 44 ? s.slice(0, 44) + '…' : s
}

export function Card({ children, className = '' }) {
  return (
    <div className={`rounded-2xl bg-white/5 border border-white/10 backdrop-blur card-in tilt-3d ${className}`}>
      {children}
    </div>
  )
}

export function PageTitle({ icon, title, desc }) {
  return (
    <div className="mb-5 card-in">
      <h1 className="text-2xl md:text-3xl font-bold tracking-tight">
        {icon}{' '}
        <span className="bg-gradient-to-r from-sky-300 via-blue-300 to-violet-300 bg-clip-text text-transparent">
          {title}
        </span>
      </h1>
      {desc && <p className="text-slate-400 text-sm mt-1">{desc}</p>}
    </div>
  )
}

export function Stat({ label, value, sub, accent = 'text-white' }) {
  return (
    <Card className="p-4 relative overflow-hidden">
      {/* thin glow line on top — lights up with the accent colour */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-blue-400/50 to-transparent" />
      <div className="text-xs uppercase tracking-wider text-slate-400">{label}</div>
      <div className={`text-2xl font-bold mt-1 tabular ${accent}`}>{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
    </Card>
  )
}

export function Panel({ title, children, className = '', right }) {
  return (
    <Card className={`p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="text-sm text-slate-300 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400/80 shrink-0" />
          {title}
        </div>
        {right}
      </div>
      {children}
    </Card>
  )
}

export function ProductCard({ p, showScore }) {
  const [open, setOpen] = useState(false)
  const hasDetail = !!p.fields
  return (
    <>
      <div onClick={() => hasDetail && setOpen(true)}
           className={`rounded-xl bg-white/5 border border-white/10 overflow-hidden transition ${hasDetail ? 'cursor-pointer hover:border-cyan-400/50 hover:bg-white/10' : ''}`}>
        <img src={p.image_url} alt="" loading="lazy" className="w-full h-24 object-cover bg-white/5"
             onError={e => { e.currentTarget.style.opacity = 0.15 }} />
        <div className="p-2">
          <div className="text-xs font-medium truncate" title={p.name}>{p.name}</div>
          <div className="text-xs text-slate-400 flex justify-between mt-0.5">
            <span className="truncate">{p.category}</span>
            <span className="text-emerald-400 ml-1">${p.price}</span>
          </div>
          {showScore && <div className="text-[10px] text-cyan-400/70 mt-0.5">match {p.score}</div>}
          {hasDetail && <div className="text-[10px] text-cyan-400/60 mt-1">click to view all fields →</div>}
        </div>
      </div>
      {open && <ProductModal p={p} onClose={() => setOpen(false)} />}
    </>
  )
}

// A big, readable detail popup (replaces the tiny inline dropdown)
export function ProductModal({ p, onClose }) {
  const fields = p.fields || {}
  const skipped = p.skipped || []
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-slate-900 border border-white/15 rounded-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto shadow-2xl"
           onClick={e => e.stopPropagation()}>
        <div className="flex gap-4 p-5 border-b border-white/10">
          <img src={p.image_url} alt="" className="w-28 h-28 rounded-xl object-cover bg-white/5 shrink-0"
               onError={e => { e.currentTarget.style.opacity = 0.15 }} />
          <div className="flex-1 min-w-0">
            <div className="text-lg font-bold truncate">{p.name}</div>
            <div className="text-sm text-slate-400">{fields.brand || p.brand || '—'} · {p.category}</div>
            <div className="text-2xl font-bold text-emerald-400 mt-1">${p.price}</div>
            <div className="mt-2 inline-flex items-center gap-2 text-xs rounded-full bg-cyan-500/15 border border-cyan-500/30 px-3 py-1 text-cyan-300">
              🤖 AI embedding: {p.embedding_dims || 3072} numbers
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-xl leading-none">✕</button>
        </div>
        <div className="p-5">
          <div className="text-sm font-semibold text-emerald-400 mb-2">✅ Filled fields ({Object.keys(fields).length})</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-0.5 text-sm">
            {Object.entries(fields).map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3 border-b border-white/5 py-1.5">
                <span className="text-slate-500">{k}</span>
                <span className="text-slate-200 text-right truncate max-w-[62%]" title={String(v)}>{fmtVal(v)}</span>
              </div>
            ))}
          </div>
          {skipped.length > 0 && (
            <div className="mt-5">
              <div className="text-sm font-semibold text-amber-400 mb-2">⏭️ Skipped fields ({skipped.length})</div>
              <div className="flex flex-wrap gap-2">
                {skipped.map(f => <span key={f} className="text-xs rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 px-2.5 py-1">{f}</span>)}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// A clean TABLE view for a product list (click "View" -> the modal)
export function ProductTable({ products }) {
  const [sel, setSel] = useState(null)
  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-400 text-xs border-b border-white/10">
              <th className="text-left py-2 pl-2">Product</th>
              <th className="text-left">Category</th>
              <th className="text-left">Brand</th>
              <th className="text-right">Price</th>
              <th className="text-center">Fields</th>
              <th className="text-center">AI dims</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {products.map((p, i) => (
              <tr key={`${p.id}-${i}`} className="border-b border-white/5 hover:bg-white/5 transition">
                <td className="py-2 pl-2">
                  <div className="flex items-center gap-2">
                    <img src={p.image_url} alt="" className="w-9 h-9 rounded object-cover bg-white/5 shrink-0"
                         onError={e => { e.currentTarget.style.opacity = 0.15 }} />
                    <span className="truncate max-w-[170px]" title={p.name}>{p.name}</span>
                  </div>
                </td>
                <td className="text-slate-400">{p.category}</td>
                <td className="text-slate-400">{(p.fields || {}).brand || '—'}</td>
                <td className="text-right text-emerald-400">${p.price}</td>
                <td className="text-center text-slate-300">{p.fields ? Object.keys(p.fields).length : '—'}</td>
                <td className="text-center text-cyan-400">{p.embedding_dims || '—'}</td>
                <td className="text-right pr-2">
                  <button onClick={() => setSel(p)}
                          className="text-xs rounded-lg bg-cyan-500/20 text-cyan-300 px-3 py-1 hover:bg-cyan-500/30 transition">View</button>
                </td>
              </tr>
            ))}
            {products.length === 0 && (
              <tr><td colSpan="7" className="text-slate-500 text-sm py-4 text-center">No products yet — run the connector.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {sel && <ProductModal p={sel} onClose={() => setSel(null)} />}
    </>
  )
}
