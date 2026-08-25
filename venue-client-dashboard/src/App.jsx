// =====================================================================
// 🧭 VENUE PORTAL SHELL — auth gate, sidebar, mobile nav, blu assistant
// (built from the proven bCloud portal kit; talks to venue-portal-api)
// =====================================================================
import { useEffect, useState } from 'react'
import { getToken, getClient, clearSession, setLogoutHandler } from './api.js'
import LoginPage from './pages/LoginPage.jsx'
import OverviewPage from './pages/OverviewPage.jsx'
import ActivityPage from './pages/ActivityPage.jsx'
import ProductsPage from './pages/ProductsPage.jsx'
import TrendingPage from './pages/TrendingPage.jsx'
import SystemPage from './pages/SystemPage.jsx'
import BluAssistant from './BluAssistant.jsx'

const NAV = [
  { id: 'overview', label: 'Overview',      icon: '📊' },
  { id: 'activity', label: 'Live activity', icon: '🛰️' },
  { id: 'trending', label: 'Trending',      icon: '🔥' },
  { id: 'products', label: 'Products',      icon: '🖼️' },
]
// 👑 the machine-room page appears only for the admin login
const NAV_ADMIN = [...NAV, { id: 'system', label: 'System', icon: '🖥️' }]

const applyTheme = (t) =>
  document.documentElement.classList.toggle('dark', t === 'dark')
applyTheme(localStorage.getItem('venue_theme') || 'light')

export default function App() {
  const [client, setClient] = useState(getToken() ? getClient() : null)
  const [page, setPage] = useState(localStorage.getItem('venue_page') || 'overview')
  const [theme, setTheme] = useState(localStorage.getItem('venue_theme') || 'light')

  useEffect(() => { setLogoutHandler(() => setClient(null)) }, [])
  const goTo = (p) => { setPage(p); localStorage.setItem('venue_page', p) }
  const signOut = () => { clearSession(); setClient(null) }
  const flipTheme = () => {
    const t = theme === 'dark' ? 'light' : 'dark'
    setTheme(t); localStorage.setItem('venue_theme', t); applyTheme(t)
  }

  if (!client) return <LoginPage onSignedIn={(c) => { setClient(c); goTo('overview') }} />

  const common = { client, goTo }
  const Page = {
    overview: <OverviewPage {...common} />,
    activity: <ActivityPage {...common} />,
    trending: <TrendingPage {...common} />,
    products: <ProductsPage {...common} />,
    ...(client.role === 'admin' ? { system: <SystemPage {...common} /> } : {}),
  }[page] || <OverviewPage {...common} />

  return (
    <div id="app-root" className="min-h-screen flex">
      <BluAssistant client={client} />

      {/* desktop sidebar */}
      <aside className="hidden md:flex flex-col w-56 shrink-0 border-r border-white/10
                        bg-black/20 p-4 sticky top-0 h-screen">
        <div className="text-center mb-1">
          <div className="text-lg font-extrabold leading-tight">
            <span className="text-mint">Venue</span> Marketplace</div>
          <div className="text-[10px] text-mist tracking-widest mt-1 mb-4">
            AI SEARCH PORTAL</div>
        </div>
        <nav className="flex-1 space-y-1">
          {(client.role === 'admin' ? NAV_ADMIN : NAV).map(n => (
            <button key={n.id} onClick={() => goTo(n.id)}
                    className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm
                                transition ${page === n.id
                                  ? 'bg-mint/15 text-foam border border-mint/30'
                                  : 'text-mist hover:bg-white/5 border border-transparent'}`}>
              <span>{n.icon}</span><span>{n.label}</span>
            </button>
          ))}
        </nav>
        <div className="pt-3 border-t border-white/10 space-y-2.5">
          <button onClick={flipTheme}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-xl
                             text-xs bg-white/5 border border-white/10 text-mist
                             hover:bg-white/10 transition">
            <span>{theme === 'dark' ? '🌙 Dark mode' : '☀️ Light mode'}</span>
          </button>
          <div className="flex items-center gap-2.5 px-1">
            <div className="w-8 h-8 rounded-full bg-mint/20 border border-mint/40
                            flex items-center justify-center text-mint font-extrabold text-sm">
              V
            </div>
            <div className="min-w-0">
              <div className="text-xs font-semibold truncate">{client.name}</div>
              <button onClick={signOut} className="text-[11px] text-mist hover:text-coral
                                                   transition">sign out →</button>
            </div>
          </div>
        </div>
      </aside>

      {/* main */}
      <main className="flex-1 min-w-0 p-4 md:p-6 pb-24 md:pb-6">
        <div className="md:hidden flex items-center justify-between mb-4">
          <div className="font-extrabold"><span className="text-mint">Venue</span> Marketplace</div>
          <div className="flex items-center gap-3">
            <button onClick={flipTheme} className="text-base">
              {theme === 'dark' ? '🌙' : '☀️'}</button>
            <button onClick={signOut} className="text-xs text-mist">sign out →</button>
          </div>
        </div>
        {Page}
        <div className="text-center text-[10px] text-mist/60 mt-10">
          Venue Marketplace · AI Search Portal · powered by bCloud AI
        </div>
      </main>

      {/* mobile bottom nav */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-black/70 backdrop-blur
                      border-t border-white/10 flex justify-around py-2">
        {(client.role === 'admin' ? NAV_ADMIN : NAV).map(n => (
          <button key={n.id} onClick={() => goTo(n.id)}
                  className={`flex flex-col items-center gap-0.5 px-1 py-1 rounded-lg text-[10px]
                              transition ${page === n.id ? 'text-mint' : 'text-mist'}`}>
            <span className="text-base">{n.icon}</span>{n.label.split(' ')[0]}
          </button>
        ))}
      </nav>
    </div>
  )
}
