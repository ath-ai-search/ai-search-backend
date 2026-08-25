// =====================================================================
// 🧩 INSTALL & KEYS — the API domain, every shop API ready to copy,
// and a LIVE search preview that hits the REAL pipeline. Venue is a
// single-store setup: no site tokens, no ?site= params — the plain
// domain is all a developer needs.
// =====================================================================
import { Fragment, useState } from 'react'
import { Panel, PageTitle, Badge } from '../ui.jsx'

const SHOP = 'https://venuemarketplace.xyz'

export default function WidgetPage() {
  const [copied, setCopied] = useState('')
  const [openApi, setOpenApi] = useState('')
  const [q, setQ] = useState('')
  const [res, setRes] = useState(null)
  const [busy, setBusy] = useState(false)

  const copy = (text, label) => {
    navigator.clipboard?.writeText(text)
    setCopied(label); setTimeout(() => setCopied(''), 1500)
  }

  // LIVE preview — the real /search on the live store
  const preview = async (e) => {
    e.preventDefault()
    if (!q.trim()) return
    setBusy(true)
    try {
      const r = await fetch(`${SHOP}/search`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q.trim(), page: 1, page_size: 6 }),
      })
      setRes(await r.json())
    } catch { setRes({ results: [], total_results: 0 }) }
    setBusy(false)
  }

  // every CLIENT-facing shop API — nothing internal, each with a one-line
  // meaning and a ready pseudo-code snippet a developer can paste
  const APIS = [
    { m: 'POST', url: `${SHOP}/search`, what: 'the AI search box',
      code: `// AI search — send what the shopper typed, get ranked products back
const r = await fetch("${SHOP}/search", {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ query: "red shoes", page: 1, page_size: 24 })
});
const { results, total_results } = await r.json();` },
    { m: 'GET', url: `${SHOP}/search/autocomplete?q=...`, what: 'type-ahead while typing',
      code: `// live suggestions under the search box while the shopper is typing
const r = await fetch("${SHOP}/search/autocomplete?q=" + encodeURIComponent(text));
const { suggestions } = await r.json();` },
    { m: 'POST', url: `${SHOP}/search/ai-assistant`, what: 'the AI shopping chat',
      code: `// AI shopping chat — shopper asks in normal words, gets answer + products
const r = await fetch("${SHOP}/search/ai-assistant", {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ message: "birthday gift for my wife under $50" })
});` },
    { m: 'POST', url: `${SHOP}/search/ai-welcome`, what: 'chat welcome + suggestion chips',
      code: `// greeting + smart suggestion chips shown when the chat window opens
const r = await fetch("${SHOP}/search/ai-welcome", {
  method: "POST", headers: { "Content-Type": "application/json" }, body: "{}"
});` },
    { m: 'GET', url: `${SHOP}/search/history`, what: "shopper's recent searches",
      code: `// read the shopper's recent searches
const { history } = await (await fetch("${SHOP}/search/history")).json();` },
    { m: 'POST', url: `${SHOP}/search/history`, what: 'save a search to history',
      code: `// save the search the shopper just made
fetch("${SHOP}/search/history", {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ query: lastSearch })
});` },
    { m: 'GET', url: `${SHOP}/similar-products?product_id=...&size=6`, what: 'similar products row',
      code: `// "similar products" row on a product page
const r = await fetch("${SHOP}/similar-products?product_id=" + id + "&size=6");` },
    { m: 'GET', url: `${SHOP}/ai-similar-products?product_id=...`, what: 'AI picks (vector similarity)',
      code: `// AI picks — products that MEAN the same thing, found by AI vectors
const r = await fetch("${SHOP}/ai-similar-products?product_id=" + id);` },
    { m: 'GET', url: `${SHOP}/trending`, what: 'trending products row',
      code: `// trending row — powered by real shopper clicks from /track
const { results } = await (await fetch("${SHOP}/trending")).json();` },
    { m: 'GET', url: `${SHOP}/popularcat`, what: 'popular categories row',
      code: `// most-loved categories in your shop right now
const r = await fetch("${SHOP}/popularcat");` },
    { m: 'GET', url: `${SHOP}/recommendations?visitor_id=...`, what: 'personal recommendations',
      code: `// personal recommendations for ONE visitor (use a stable visitor id)
const r = await fetch("${SHOP}/recommendations?visitor_id=" + vid);` },
    { m: 'GET', url: `${SHOP}/pick-up?visitor_id=...`, what: '"pick up where you left off"',
      code: `// products the visitor looked at but did not finish with
const r = await fetch("${SHOP}/pick-up?visitor_id=" + vid);` },
    { m: 'GET', url: `${SHOP}/continueshop?visitor_id=...`, what: '"continue shopping" row',
      code: `// continue-shopping row from the visitor's recent activity
const r = await fetch("${SHOP}/continueshop?visitor_id=" + vid);` },
    { m: 'GET', url: `${SHOP}/recommendation-grids?visitor_id=...`, what: 'four homepage grids in one call',
      code: `// four ready recommendation grids for the home page — one call
const r = await fetch("${SHOP}/recommendation-grids?visitor_id=" + vid);` },
    { m: 'POST', url: `${SHOP}/track`, what: 'shopper events → Trending + Live activity',
      code: `// send shopper events — feeds Trending, Recommendations AND your Live activity page
fetch("${SHOP}/track", {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ events: [{
    event_type: "click",          // view | click | add_to_cart | wishlist | purchase
    visitor_id: vid, product_id: id, query: lastSearch, value: price
  }] })
});` },
  ].map(a => ({ ...a, id: `${a.m} ${a.url}` }))

  return (
    <div>
      <PageTitle icon="🧩" title="Install & keys"
                 desc="Everything your website team needs — safe to share, read-only by design." />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <Panel title="🌐 Your API domain">
          <div className="flex items-center gap-2">
            <code className="flex-1 text-sm bg-black/25 border border-mint/25 rounded-lg
                             px-3 py-2.5 font-mono text-mint">venuemarketplace.xyz</code>
            <button onClick={() => copy('venuemarketplace.xyz', 'tok')}
                    className="text-xs px-3 py-2.5 rounded-lg bg-mint/20 border border-mint/40
                               text-mint hover:bg-mint/30 transition">
              {copied === 'tok' ? '✓' : 'copy'}</button>
          </div>
          <div className="text-[11px] text-mist mt-2">
            single-store setup — no token needed on your website; all APIs are open
            read-only + rate-limited
          </div>
        </Panel>

        <Panel title="⚡ Live preview — the REAL AI pipeline">
          <form onSubmit={preview} className="flex gap-2">
            <input value={q} onChange={e => setQ(e.target.value)}
                   placeholder="try a search on your own data…"
                   className="flex-1 rounded-xl bg-black/25 border border-white/15 px-3 py-2
                              text-sm outline-none focus:border-mint/60 transition" />
            <button disabled={busy}
                    className="rounded-xl bg-mint/90 hover:bg-mint text-white font-bold px-4
                               text-sm transition disabled:opacity-50">
              {busy ? '…' : 'Search'}</button>
          </form>
          {res && (
            <div className="mt-3 space-y-1.5 max-h-40 overflow-y-auto">
              <div className="text-[11px] text-mist">{res.total_results ?? 0} products found</div>
              {(res.results || []).slice(0, 6).map((p, i) => (
                <div key={i} className="text-sm flex justify-between rounded-lg px-3 py-1.5
                     bg-white/[0.03] border border-white/5">
                  <span className="truncate pr-2">{p.name}</span>
                  {p.price != null && <span className="text-mint text-xs">
                    ${Number(p.price).toFixed(2)}</span>}
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      <Panel title="🔌 Every API for YOUR shop — copy the URL, or press </> for ready code">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-mist text-xs border-b border-white/10">
                <th className="text-left py-2 pr-3">Method</th>
                <th className="text-left pr-3">Full API</th>
                <th className="text-left pr-3">What it does</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {APIS.map(a => (<Fragment key={a.id}>
                <tr className="border-b border-white/5 hover:bg-white/5 transition">
                  <td className={`py-2 pr-3 font-bold text-xs ${
                    a.m === 'GET' ? 'text-mint' : 'text-teal'}`}>{a.m}</td>
                  <td className="pr-3"><code className="text-[11px] text-foam opacity-80
                    whitespace-nowrap">{a.url}</code></td>
                  <td className="text-xs text-mist pr-3 whitespace-nowrap">{a.what}</td>
                  <td className="text-right whitespace-nowrap">
                    <button onClick={() => copy(a.url, a.id)}
                            className="text-xs text-mint hover:underline mr-3">
                      {copied === a.id ? '✓' : 'copy'}</button>
                    <button onClick={() => setOpenApi(openApi === a.id ? '' : a.id)}
                            className={`text-xs font-mono px-2 py-0.5 rounded border transition ${
                              openApi === a.id
                                ? 'bg-mint text-white border-mint'
                                : 'text-teal border-mint/30 hover:bg-mint/10'}`}>
                      {'</>'}</button></td>
                </tr>
                {openApi === a.id && (
                  <tr>
                    <td colSpan={4} className="pb-3 pt-1">
                      <div className="relative">
                        <pre className="text-[11px] leading-relaxed bg-[#14102b]
                             text-[#c9b8ff] rounded-xl p-4 overflow-x-auto">{a.code}</pre>
                        <button onClick={() => copy(a.code, a.id + 'c')}
                                className="absolute top-2 right-2 text-[11px] px-2.5 py-1
                                           rounded-lg bg-mint/20 border border-mint/40
                                           text-mint hover:bg-mint/30 transition">
                          {copied === a.id + 'c' ? '✓ copied' : 'copy code'}</button>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>))}
            </tbody>
          </table>
        </div>
        <div className="text-[11px] text-mist mt-3">
          These are ALL the APIs your website needs — nothing extra. Press
          <span className="font-mono text-teal"> {'</>'} </span> on any row for paste-ready
          code with a one-line explanation, or hand this page to your developer. 🧑‍💻
        </div>
      </Panel>
    </div>
  )
}
