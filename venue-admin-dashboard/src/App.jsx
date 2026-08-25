// =====================================================================
// App.jsx — the SHELL: sidebar menu + page routing + live polling
// =====================================================================
// Polls the API every 1.5s and shows one of 5 pages. The 3 status
// lights (OpenSearch / API / OpenAI) are clickable → open their pages.
// =====================================================================
import { useEffect, useState } from 'react'
import logoPng from './assets/bcloud-logo.png'
import { getStats, getHealth, getOpenSearchInfo, getApiInfo, getBilling, getFields, getClients, setApiClient } from './api.js'
import Overview from './pages/Overview.jsx'
import OpenSearchPage from './pages/OpenSearchPage.jsx'
import ApiPage from './pages/ApiPage.jsx'
import AiPage from './pages/AiPage.jsx'
import ProductsPage from './pages/ProductsPage.jsx'
import BillingPage from './pages/BillingPage.jsx'
import FieldsPage from './pages/FieldsPage.jsx'
import AzurePage from './pages/AzurePage.jsx'
import MonitorPage from './pages/MonitorPage.jsx'
import SearchAnalyticsPage from './pages/SearchAnalyticsPage.jsx'
import ClientsPage from './pages/ClientsPage.jsx'
import TicketsPage from './pages/TicketsPage.jsx'

const NAV = [
  { id: 'overview',   label: 'Overview',    icon: '📊' },
  { id: 'search',     label: 'Search',      icon: '🔎' },
  { id: 'opensearch', label: 'OpenSearch',  icon: '🔍' },
  { id: 'api',        label: 'API',         icon: '🔌' },
  { id: 'ai',         label: 'AI / OpenAI', icon: '🤖' },
  { id: 'products',   label: 'Products',    icon: '🖼️' },
  { id: 'fields',     label: 'Fields',      icon: '🗂️' },
  { id: 'billing',    label: 'Billing',     icon: '💰' },
  { id: 'azure',      label: 'Azure',       icon: '☁️' },
  { id: 'monitor',    label: 'Live Monitor', icon: '📡' },
  { id: 'clients',    label: 'Clients',     icon: '👥' },
  { id: 'tickets',    label: 'Tickets',     icon: '🎫' },
]

export default function App() {
  // refresh keeps your place: page + selected client survive reloads
  const [page, setPage] = useState(() => localStorage.getItem('dash_page') || 'overview')
  // 🚪 basic-auth "sign out": poison the cached credentials, then reload —
  // the browser forgets the login and shows the password prompt again
  const signOut = () => {
    fetch(window.location.pathname, {
      headers: { Authorization: 'Basic ' + btoa('signout:x') },
    }).finally(() => window.location.reload())
  }
  const [stats, setStats] = useState(null)
  const [health, setHealth] = useState({})
  const [osInfo, setOsInfo] = useState({})
  const [apiInfo, setApiInfo] = useState({})
  const [billing, setBilling] = useState({})
  const [fields, setFields] = useState({})
  const [pollMs, setPollMs] = useState(null)   // how fast the live poll answers

  // 👥 multi-tenant: the client list + which client's world we are viewing
  const [clients, setClients] = useState([])
  const [selClient, setSelClient] = useState(() => localStorage.getItem('dash_client') || 'default')
  setApiClient(selClient)   // keep the data layer in sync every render (idempotent)
  useEffect(() => {
    let alive = true
    const loadClients = () => getClients()
      .then(x => alive && setClients(x.clients || []))
      .catch(() => {})
    loadClients()
    const id = setInterval(loadClients, 30000)
    return () => { alive = false; clearInterval(id) }
  }, [])
  const [refreshKey, setRefreshKey] = useState(0)
  const pickClient = (id) => {
    setApiClient(id)          // every data call now carries this client
    setSelClient(id)
    localStorage.setItem('dash_client', id)
    setRefreshKey(k => k + 1) // restart the poll -> new client's data NOW
  }
  useEffect(() => { localStorage.setItem('dash_page', page) }, [page])
  // stored client no longer exists (deleted)? -> fall back to default
  useEffect(() => {
    if (clients.length && !clients.some(c => c.client_id === selClient)) pickClient('default')
  }, [clients])                                     // eslint-disable-line

  useEffect(() => {
    let alive = true
    const tick = async () => {
      const t0 = performance.now()
      const [s, h, o, a, bl, f] = await Promise.all([
        getStats().catch(() => null),
        getHealth().catch(() => ({})),
        getOpenSearchInfo().catch(() => ({})),
        getApiInfo().catch(() => ({})),
        getBilling().catch(() => ({})),
        getFields().catch(() => ({})),
      ])
      if (!alive) return
      setPollMs(Math.round(performance.now() - t0))
      if (s) setStats(s)
      if (h) setHealth(h)
      if (o) setOsInfo(o)
      if (a) setApiInfo(a)
      if (bl) setBilling(bl)
      if (f) setFields(f)
    }
    tick()
    const id = setInterval(tick, 1500)
    return () => { alive = false; clearInterval(id) }
  }, [refreshKey])

  const s = stats || {}
  const selClientObj = clients.find(c => c.client_id === selClient)
  const common = { stats: s, health, osInfo, apiInfo, billing, fields, goTo: setPage,
                   clients, selClient, selClientObj }

  const Page = {
    overview: <Overview {...common} />,
    search: <SearchAnalyticsPage {...common} />,
    opensearch: <OpenSearchPage {...common} />,
    api: <ApiPage {...common} />,
    ai: <AiPage {...common} />,
    products: <ProductsPage {...common} />,
    billing: <BillingPage {...common} />,
    fields: <FieldsPage {...common} />,
    azure: <AzurePage {...common} />,
    monitor: <MonitorPage {...common} />,
    clients: <ClientsPage {...common} />,
    tickets: <TicketsPage {...common} />,
  }[page]

  return (
    <div className="min-h-screen flex">
      {/* SIDEBAR */}
      <aside className="w-56 shrink-0 border-r border-white/10 bg-black/20 p-4 hidden md:flex flex-col gap-1 sticky top-0 h-screen">
        <div className="mb-5">
          {/* the official bCloud logo — same as the client portal; dark
              wordmark, so it sits on a soft white chip */}
          <img src={logoPng} alt="bCloud AI"
               style={{ height: 44, width: 44 * (310 / 184), background: '#ffffff',
                        borderRadius: 10, padding: '3px 8px', display: 'block',
                        marginBottom: 8 }} />
          <div className="text-sm font-bold text-cyan-400">🎪 VENUE Console</div>
          <div className="mt-1 inline-block rounded-full bg-cyan-500/15 border border-cyan-500/30 px-2 py-0.5 text-[10px] text-cyan-300">
            admin.venuemarketplace.xyz
          </div>
        </div>
        {NAV.map(n => (
          <button key={n.id} onClick={() => setPage(n.id)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition ${
                    page === n.id ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                                  : 'text-slate-300 hover:bg-white/5'}`}>
            <span>{n.icon}</span><span>{n.label}</span>
          </button>
        ))}
        {/* clickable status lights -> open detail pages */}
        <div className="mt-auto pt-4 border-t border-white/10 space-y-1">
          {/* 🚪 sign out (basic-auth reset) */}
          <button onClick={signOut}
                  className="w-full text-[11px] px-2 py-1.5 mb-2 rounded-lg bg-red-500/10 border
                             border-red-500/30 text-red-300 hover:bg-red-500/20 transition">
            🚪 Sign out</button>
          <div className="flex items-center justify-between px-1 mb-2">
            <span className="text-[10px] uppercase tracking-wider text-slate-500">System (click)</span>
            <span className="flex items-center gap-1.5 text-[10px] text-slate-500">
              <span className={`w-1.5 h-1.5 rounded-full pulse-dot ${health.status === 'ok' ? 'bg-emerald-400' : 'bg-red-400'}`} />
              live{pollMs != null ? ` · ${pollMs}ms` : ''}
            </span>
          </div>
          <StatusLink on={health.opensearch}       label="OpenSearch" onClick={() => setPage('opensearch')} />
          <StatusLink on={health.status === 'ok'}   label="API"        onClick={() => setPage('api')} />
          <StatusLink on={health.status === 'ok'}   label="OpenAI"     onClick={() => setPage('ai')} />
        </div>
      </aside>

      {/* CONTENT */}
      <main className="flex-1 min-w-0 p-3 sm:p-5 md:p-8">
        {/* mobile brand — the sidebar is hidden on phones */}
        <div className="md:hidden flex items-center gap-2 mb-2">
          <img src={logoPng} alt="bCloud AI"
               style={{ height: 30, width: 30 * (310 / 184), background: '#ffffff',
                        borderRadius: 8, padding: '2px 6px', display: 'block' }} />
          <span className="text-xs font-bold text-cyan-400">🎪 VENUE Console</span>
          {/* 🚪 sign out — the sidebar (with its sign-out button) is hidden on phones */}
          <button onClick={signOut}
                  className="ml-auto text-[11px] px-2.5 py-1.5 rounded-lg bg-red-500/10 border
                             border-red-500/30 text-red-300 hover:bg-red-500/20 transition whitespace-nowrap">
            🚪 Sign out</button>
        </div>
        {/* mobile nav */}
        <div className="md:hidden flex gap-2 overflow-x-auto mb-4 pb-2 -mx-3 px-3 sm:-mx-5 sm:px-5 sticky top-0 z-20 bg-slate-950/90 backdrop-blur py-2">
          {NAV.map(n => (
            <button key={n.id} onClick={() => setPage(n.id)}
                    className={`px-3 py-2.5 rounded-lg text-sm whitespace-nowrap ${
                      page === n.id ? 'bg-cyan-500/20 text-cyan-300' : 'bg-white/5 text-slate-300'}`}>
              {n.icon} {n.label}
            </button>
          ))}
        </div>
        {/* 👥 CLIENT SWITCHER — appears by itself once a 2nd client exists.
            Azure + Live Monitor + Clients pages are GLOBAL (no switch). */}
        {clients.length > 1 && !['azure', 'monitor', 'clients', 'api', 'tickets'].includes(page) && (
          <div className="flex items-center gap-2 mb-4 flex-wrap card-in">
            <span className="text-[11px] uppercase tracking-wider text-slate-500 mr-1">Viewing client:</span>
            {clients.map(c => (
              <button key={c.client_id} onClick={() => pickClient(c.client_id)}
                      className={`px-3 py-1.5 rounded-full text-xs font-semibold transition border ${
                        selClient === c.client_id
                          ? 'bg-cyan-500/25 text-cyan-200 border-cyan-400/50'
                          : 'bg-white/5 text-slate-400 border-white/10 hover:bg-white/10'}`}>
                {c.name}
                {c.products != null && <span className="ml-1.5 opacity-60">{c.products}</span>}
              </button>
            ))}
          </div>
        )}
        {Page}
        <div className="text-center text-xs text-slate-600 mt-8">
          AI Search · 🎪 Venue Console
          {clients.length > 1 && !['azure', 'monitor', 'clients', 'api', 'tickets'].includes(page) &&
            <span> · viewing: {selClientObj?.name || selClient}</span>} · polls live every 1.5s
        </div>
      </main>
    </div>
  )
}

function StatusLink({ on, label, onClick }) {
  return (
    <button onClick={onClick}
            className="w-full flex items-center justify-between gap-2 px-3 py-1.5 rounded-lg text-xs hover:bg-white/5 transition">
      <span className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${on ? 'bg-emerald-400' : 'bg-red-400'}`} />
        {label}
      </span>
      <span className="text-slate-500">→</span>
    </button>
  )
}
