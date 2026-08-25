// Products page — search + browse EVERY indexed product ("Show more")
import { useState, useEffect } from 'react'
import { PageTitle, Panel, ProductCard, ProductTable, fmtMoney } from '../ui.jsx'
import { search, getProducts } from '../api.js'

const PAGE = 30                       // how many more each click loads

export default function ProductsPage({ stats, selClient }) {
  const s = stats || {}
  const [q, setQ] = useState('')
  const [results, setResults] = useState([])
  const [info, setInfo] = useState(null)
  const [busy, setBusy] = useState(false)

  // ---- browse ALL products straight from the database ----
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)

  const loadMore = async (reset = false) => {
    setLoading(true)
    const offset = reset ? 0 : items.length
    const r = await getProducts(offset, PAGE).catch(() => null)
    if (r) {
      setItems(prev => (reset ? r.items : [...prev, ...r.items]))
      setTotal(r.total || 0)
    }
    setLoading(false)
  }

  // first load + FULL RESET whenever the client switcher changes —
  // otherwise the list keeps showing the PREVIOUS client's products
  useEffect(() => {
    setItems([]); setTotal(0); setResults([]); setInfo(null)
    loadMore(true)
  }, [selClient])                                   // eslint-disable-line
  useEffect(() => {
    if (s.indexed && total && s.indexed !== total) loadMore(true)
  }, [s.indexed])                                   // eslint-disable-line

  const doSearch = async (e) => {
    e?.preventDefault()
    if (!q.trim()) return
    setBusy(true)
    const r = await search(q, 12).catch(() => ({ results: [] }))
    setResults(r.results || [])
    setInfo({ cost: r.search_cost || 0, tokens: r.tokens || 0, count: (r.results || []).length })
    setBusy(false)
  }

  return (
    <div>
      <PageTitle icon="🖼️" title="Products" desc="Search the catalog by meaning, and inspect every indexed product's fields." />

      <Panel title="🔍 Semantic search (by meaning)" className="mb-4">
        <div className="text-xs text-slate-500 mb-3">Each search embeds your query with the AI (a tiny cost — tracked on the AI page).</div>
        <form onSubmit={doSearch} className="flex gap-2 mb-2">
          <input value={q} onChange={e => setQ(e.target.value)}
                 placeholder="try: shoes for running · gift for someone who cooks · cheap gaming console"
                 className="flex-1 rounded-xl bg-white/10 border border-white/10 px-4 py-2.5 outline-none focus:border-cyan-400 transition" />
          <button className="rounded-xl bg-cyan-500 hover:bg-cyan-400 px-6 py-2.5 font-semibold text-slate-900 transition">
            {busy ? '...' : 'Search'}
          </button>
        </form>
        {info && (
          <div className="text-xs text-slate-400 mb-3">
            Found {info.count} · this search used {info.tokens} tokens ≈
            <span className="text-emerald-400"> {fmtMoney(info.cost)}</span>
          </div>
        )}
        <div className="grid grid-cols-1 xs:grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {results.map((r, i) => <ProductCard key={`res-${r.id}-${i}`} p={r} showScore />)}
          {results.length === 0 && <div className="text-slate-500 text-sm col-span-full">Type a query and hit Search.</div>}
        </div>
      </Panel>

      <Panel title={`🗂️ All indexed products — showing ${items.length} of ${total.toLocaleString()}`}>
        <div className="text-xs text-slate-500 mb-3">
          Read live from the database — click “View” on any row for the full field detail.
        </div>

        <ProductTable products={items} />

        {/* ---- Show more / all loaded ---- */}
        <div className="mt-4 flex flex-col items-center gap-2">
          {items.length < total ? (
            <button onClick={() => loadMore(false)} disabled={loading}
                    className="rounded-xl bg-cyan-500/20 border border-cyan-400/40 text-cyan-200
                               hover:bg-cyan-500/30 disabled:opacity-50 px-6 py-2.5 font-semibold transition">
              {loading ? 'Loading…' : `Show ${Math.min(PAGE, total - items.length)} more`}
            </button>
          ) : (
            total > 0 && <div className="text-xs text-slate-500">
              All {total.toLocaleString()} products loaded ✅
            </div>
          )}

          {total > 0 && (
            <div className="w-full max-w-sm h-1.5 rounded-full bg-white/10 overflow-hidden">
              <div className="h-full bg-cyan-400 transition-all duration-500"
                   style={{ width: `${Math.min(100, items.length / total * 100)}%` }} />
            </div>
          )}

          {total === 0 && !loading &&
            <div className="text-sm text-slate-500">No products indexed yet.</div>}
        </div>
      </Panel>
    </div>
  )
}
