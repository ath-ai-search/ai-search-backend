// API page — TWO API families with a TAB SWITCHER (short page, no scroll-wall):
//   🏢 Ingestion API  (the /docs portal)      — clients push products in
//   🛍️ AI Search API  (the /shop/docs portal) — shoppers search, 21 endpoints
// BOTH tabs have a live requests-per-endpoint chart. The search catalogue +
// its counts are read LIVE from the search API itself (nothing hardcoded).
import { useEffect, useState } from 'react'
import {
  BarChart, Bar, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid,
} from 'recharts'
import { Stat, PageTitle, Panel, TT, DONUT } from '../ui.jsx'
import { getShopApiInfo, getClients } from '../api.js'

const ENDPOINTS = [
  // ---- INGESTION (the client uses these) ----
  { m: 'POST', path: '/ingest/products', who: 'CLIENT ⭐', desc: 'send many products (the API we give the client)' },
  { m: 'POST', path: '/ingest/product', who: 'CLIENT', desc: 'send one product' },
  { m: 'POST', path: '/ingest/start', who: 'CLIENT', desc: 'begin a run (fresh index + reset dashboard)' },
  { m: 'GET', path: '/health', who: 'client / us', desc: 'is the API + OpenSearch alive?' },
  // ---- DASHBOARD ----
  { m: 'GET', path: '/stats', who: 'DASHBOARD', desc: 'live dashboard data' },
  { m: 'GET', path: '/opensearch-info', who: 'DASHBOARD', desc: 'OpenSearch details page' },
  { m: 'GET', path: '/api-info', who: 'DASHBOARD', desc: 'this API page' },
  { m: 'GET', path: '/search', who: 'DASHBOARD', desc: 'semantic search (test box)' },
  // ---- FIELDS API (client, dynamic schema) ----
  { m: 'POST', path: '/fields/register', who: 'CLIENT ⭐', desc: "register THEIR field names -> dynamic index (API 1)" },
  { m: 'GET', path: '/fields', who: 'client / us', desc: 'view the registered field mapping' },
  // ---- BILLING ----
  { m: 'GET', path: '/billing/summary', who: 'DASHBOARD', desc: 'months, runs, totals' },
  { m: 'GET', path: '/billing/pdf', who: 'DASHBOARD', desc: 'monthly PDF invoice' },
]

const TAG_ICONS = {
  search: '🔍', autocomplete: '⌨️', assistant: '🤖', ai: '🤖', welcome: '👋',
  tracking: '📈', history: '🕘', similar: '🧲', trending: '🔥',
  recommendations: '🎁', widget: '🧩', stats: '📊', other: '🔹',
}

function MethodChip({ m }) {
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
      m === 'POST' ? 'bg-emerald-500/20 text-emerald-300'
      : m === 'DELETE' ? 'bg-rose-500/20 text-rose-300'
      : 'bg-sky-500/20 text-sky-300'}`}>{m}</span>
  )
}

// keep the endpoint-name gutter narrow so the bars stay readable on phones
const shortPath = (n) => (String(n).length > 14 ? String(n).slice(0, 13) + '…' : n)

function TrafficChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height="86%">
      <BarChart data={data} layout="vertical" margin={{ top: 5, right: 24, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
        <XAxis type="number" stroke="#64748b" tick={{ fontSize: 11 }} allowDecimals={false} />
        <YAxis type="category" dataKey="name" stroke="#64748b" tick={{ fontSize: 10 }} width={90} tickFormatter={shortPath} />
        <Tooltip {...TT} />
        <Bar isAnimationActive={false} dataKey="value" name="requests" radius={[0, 4, 4, 0]}>
          {data.map((_, i) => <Cell key={i} fill={DONUT[i % DONUT.length]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export default function ApiPage({ apiInfo }) {
  const [tab, setTab] = useState('ingest')

  // 🏢 ingestion traffic (live from the main poll)
  const a = apiInfo || {}
  const eps = Object.entries(a.endpoints || {})
    .map(([k, v]) => ({ name: k.replace('GET ', '').replace('POST ', ''), value: v }))
    .sort((x, y) => y.value - x.value)

  // 🛍️ search API catalogue + LIVE counts (own poll, every 15s)
  const [shop, setShop] = useState(null)
  useEffect(() => {
    let alive = true
    const load = () => getShopApiInfo().then(x => alive && setShop(x)).catch(() => alive && setShop(s => s || { ok: false, endpoints: [] }))
    load()
    const id = setInterval(load, 15000)
    return () => { alive = false; clearInterval(id) }
  }, [])
  const shopEps = shop?.endpoints || []
  const shopTraffic = shopEps
    .filter(e => (e.count || 0) > 0)
    .map(e => ({ name: e.path.replace('/shop', ''), value: e.count }))
    .sort((x, y) => y.value - x.value)
    .slice(0, 12)
  const tags = [...new Set(shopEps.map(e => e.tag))]

  // 👥 client picker for the URL preview — shows each endpoint EXACTLY as that
  // client's code must call it (real site token included, key=hidden by design)
  const [clients, setClients] = useState([])
  const [tokClient, setTokClient] = useState('default')
  useEffect(() => {
    getClients().then(d => {
      const act = (d.clients || []).filter(c => c.status === 'active')
      setClients(act)
      if (act.length && !act.some(c => c.client_id === 'default')) setTokClient(act[0].client_id)
    }).catch(() => {})
  }, [])
  const selC = clients.find(c => c.client_id === tokClient)
  // every client shows a FULL url — client 1's token is literally "default"
  // (and its calls also work with no token at all, since it IS the default world)
  const siteTok = (selC && selC.site_token) || ''
  const BASE = window.location.origin

  const TabBtn = ({ id, children }) => (
    <button onClick={() => setTab(id)}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition border ${
              tab === id ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                         : 'bg-white/5 text-slate-400 border-white/10 hover:bg-white/10'}`}>
      {children}
    </button>
  )

  return (
    <div>
      <PageTitle icon="🔌" title="APIs"
                 desc="Both API families on this server — switch between them below." />

      {/* 🌐 honesty label: traffic counters are infrastructure-wide */}
      <div className="mb-4 card-in">
        <span className="inline-flex items-center gap-2 text-xs rounded-full bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 text-emerald-300">
          🌐 GLOBAL VIEW — request counters cover ALL clients together (server traffic monitoring, like the Azure page)
        </span>
      </div>

      {/* ---------- THE SWITCHER ---------- */}
      <div className="flex flex-wrap gap-2 mb-5 card-in">
        <TabBtn id="ingest">🏢 Ingestion API <span className="text-slate-500 font-normal">/docs</span></TabBtn>
        <TabBtn id="shop">🛍️ Shop / Search API <span className="text-slate-500 font-normal">/shop/docs</span></TabBtn>
      </div>

      {/* ================== TAB 1 — INGESTION ================== */}
      {tab === 'ingest' && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
            <Stat label="Total requests" value={a.total_requests || 0} sub="since the API started" accent="text-cyan-400" />
            <Stat label="Active endpoints" value={eps.length} sub="unique routes hit" accent="text-violet-400" />
            <Stat label="Given to client" value={<span className="text-lg break-all">/ingest/*</span>} sub="the 3 ingest endpoints" accent="text-emerald-400" />
          </div>

          <Panel title="📊 Requests per endpoint (live)" className="h-60 md:h-72 mb-4">
            {eps.length ? <TrafficChart data={eps} />
              : <div className="text-sm text-slate-500 py-6">no traffic yet</div>}
          </Panel>

          <Panel title="📋 Ingestion + dashboard endpoints">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-slate-400 text-xs border-b border-white/10">
                    <th className="text-left py-2 pr-3">Method</th>
                    <th className="text-left pr-3">Full API (as used in code)</th>
                    <th className="text-left pr-3">Used by</th>
                    <th className="text-left pr-3">Identity in the call</th>
                    <th className="text-left">What it does</th>
                  </tr>
                </thead>
                <tbody>
                  {ENDPOINTS.map(e => (
                    <tr key={e.path} className="border-b border-white/5 hover:bg-white/5 transition">
                      <td className="py-2 pr-3"><MethodChip m={e.m} /></td>
                      <td className="font-mono text-xs text-slate-200 pr-3 whitespace-nowrap">{BASE}{e.path}</td>
                      <td className="text-xs text-slate-400 pr-3">{e.who}</td>
                      <td className="font-mono text-[11px] pr-3 whitespace-nowrap">
                        {e.who.startsWith('CLIENT')
                          ? <span className="text-amber-300">X-API-Key: &lt;client's key&gt;</span>
                          : e.who.includes('client')
                            ? <span className="text-slate-400">key optional</span>
                            : <span className="text-slate-500">dashboard login</span>}
                      </td>
                      <td className="text-xs text-slate-400">{e.desc}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="text-[11px] text-slate-600 mt-3">
              🔑 The key IS the identity: the server hashes it → finds the client → routes data to
              their own index. Keys are shown ONCE at creation (Clients page) and stored only as
              fingerprints — that's why no real key can be displayed here.
            </div>
          </Panel>
        </>
      )}

      {/* ================== TAB 2 — SHOP / SEARCH ================== */}
      {tab === 'shop' && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
            <Stat label="Total requests" value={shop == null ? '…' : (shop.total_requests || 0)}
                  sub="live from the search API" accent="text-cyan-400" />
            <Stat label="Search endpoints" value={shop == null ? '…' : (shop.total || 0)}
                  sub="read live from its OpenAPI spec" accent="text-violet-400" />
            <Stat label="Groups" value={shop == null ? '…' : tags.length}
                  sub="search · AI · tracking · trending…" accent="text-emerald-400" />
          </div>

          <Panel title="📊 Requests per endpoint (live)" className="h-60 md:h-72 mb-4">
            {shopTraffic.length ? <TrafficChart data={shopTraffic} />
              : <div className="text-sm text-slate-500 py-6">
                  no shopper traffic yet — the widget's searches will appear here live
                </div>}
          </Panel>

          <Panel title="🛍️ All search endpoints — live from /shop's own specification">
            {clients.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap mb-3">
                <span className="text-[11px] text-slate-500 uppercase tracking-wider">show URLs as used by</span>
                {clients.map(c => (
                  <button key={c.client_id} onClick={() => setTokClient(c.client_id)}
                          className={`px-3 py-1 rounded-full text-xs font-semibold border transition ${
                            tokClient === c.client_id
                              ? 'bg-blue-600/40 border-blue-400/50 text-white'
                              : 'bg-white/5 border-white/10 text-slate-400 hover:bg-white/10'}`}>
                    {c.name || c.client_id}
                  </button>
                ))}
                <span className="text-[11px] text-slate-500">
                  → every call carries <span className="font-mono text-emerald-300">?site={siteTok || '…'}</span>
                  {siteTok === 'default' && <> (client 1 also works with no token — it is the default world)</>}
                </span>
              </div>
            )}
            {shop == null && <div className="text-sm text-slate-500 py-4">loading the catalogue…</div>}
            {shop?.ok === false && (
              <div className="text-sm text-amber-400 py-4">
                ⚠️ Could not read the search API's specification right now ({shop.error || 'unreachable'}) — check the Azure page probes.
              </div>
            )}
            {shopEps.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-slate-400 text-xs border-b border-white/10">
                      <th className="text-left py-2 pr-3">Method</th>
                      <th className="text-left pr-3">Endpoint</th>
                      <th className="text-left pr-3">Group</th>
                      <th className="text-right pr-3">Requests</th>
                      <th className="text-left">What it does</th>
                    </tr>
                  </thead>
                  <tbody>
                    {shopEps.map(e => (
                      <tr key={e.method + e.path} className="border-b border-white/5 hover:bg-white/5 transition">
                        <td className="py-2 pr-3"><MethodChip m={e.method} /></td>
                        <td className="font-mono text-xs text-slate-200 pr-3 whitespace-nowrap">
                          {BASE}{e.path}
                          {siteTok && <span className="text-emerald-300">?site={siteTok}</span>}
                        </td>
                        <td className="text-xs text-slate-400 pr-3">{TAG_ICONS[e.tag?.toLowerCase()] || '🔹'} {e.tag}</td>
                        <td className="text-right text-xs text-cyan-300 pr-3 tabular">{e.count || 0}</td>
                        <td className="text-xs text-slate-400">{e.summary || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="text-[11px] text-slate-600 mt-3">
              List + counts come live from the search API itself — a new endpoint there appears here automatically.
              Try them at <span className="text-violet-300 font-mono">/shop/docs</span>.
            </div>
          </Panel>
        </>
      )}
    </div>
  )
}
