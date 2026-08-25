// =====================================================================
// 🧭 APP SHELL — auth gate, desktop sidebar, MOBILE bottom nav (the
// reference portal had no mobile at all), page routing, sign-out.
// =====================================================================
import { useEffect, useState } from 'react'
import { getToken, getClient, clearSession, setLogoutHandler } from './api.js'
import LoginPage from './pages/LoginPage.jsx'
import OverviewPage from './pages/OverviewPage.jsx'
import AnalyticsPage from './pages/AnalyticsPage.jsx'
import EventsPage from './pages/EventsPage.jsx'
import BluAssistant from './BluAssistant.jsx'
import BrandLogo from './BrandLogo.jsx'
import ProductsPage from './pages/ProductsPage.jsx'
import BillingPage from './pages/BillingPage.jsx'
import SyncPage from './pages/SyncPage.jsx'
import SearchSettingsPage from './pages/SearchSettingsPage.jsx'
import WidgetPage from './pages/WidgetPage.jsx'
import SupportPage from './pages/SupportPage.jsx'
import SettingsPage from './pages/SettingsPage.jsx'

const NAV = [
  { id: 'overview',        label: 'Overview',        icon: '📊' },
  { id: 'analytics',       label: 'Analytics',       icon: '🔎' },
  { id: 'events',          label: 'Live activity',   icon: '🛰️' },
  { id: 'products',        label: 'Products',        icon: '🖼️' },
  { id: 'billing',         label: 'Billing',         icon: '💰' },
  { id: 'sync',            label: 'Data sync',       icon: '🔄' },
  { id: 'search-settings', label: 'Search settings', icon: '🎛️' },
  { id: 'widget',          label: 'Install & keys',  icon: '🧩' },
  { id: 'support',         label: 'Support',         icon: '🎫' },
  { id: 'settings',        label: 'Settings',        icon: '⚙️' },
]
const MOBILE_NAV = ['overview', 'analytics', 'events', 'products', 'billing', 'support']

// 🌙 theme is applied on the <html> element so EVERY page (login too) follows;
// applied at import time so there is no light flash before React mounts
const applyTheme = (t) =>
  document.documentElement.classList.toggle('dark', t === 'dark')
applyTheme(localStorage.getItem('portal_theme') || 'light')

export default function App() {
  const [client, setClient] = useState(getToken() ? getClient() : null)
  const [page, setPage] = useState(localStorage.getItem('portal_page') || 'overview')
  const [theme, setTheme] = useState(localStorage.getItem('portal_theme') || 'light')
  const [arrow, setArrow] = useState(null)   // {x, y} — Blu's "here it is!" pointer

  useEffect(() => { setLogoutHandler(() => setClient(null)) }, [])
  const goTo = (p) => { setPage(p); localStorage.setItem('portal_page', p) }
  const signOut = () => { clearSession(); setClient(null) }
  const flipTheme = () => {
    const t = theme === 'dark' ? 'light' : 'dark'
    setTheme(t); localStorage.setItem('portal_theme', t); applyTheme(t)
  }

  // 🎯 Blu's "show me" — open the page, find the section, point at it
  const spotlight = (targetPage, find) => {
    goTo(targetPage)
    setTimeout(() => {
      const cards = [...document.querySelectorAll('.rounded-card')]
      const el = (find && cards.find(c =>
        c.textContent.toLowerCase().includes(find.toLowerCase())))
        || document.querySelector('main h1')
      if (!el) return
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      el.classList.add('blu-highlight')
      setTimeout(() => {
        const r = el.getBoundingClientRect()
        setArrow({ x: r.left + r.width / 2, y: Math.max(70, r.top - 8) })
      }, 550)
      setTimeout(() => { el.classList.remove('blu-highlight'); setArrow(null) }, 5200)
    }, 450)
  }

  if (!client) return <LoginPage onSignedIn={(c) => { setClient(c); goTo('overview') }} />

  const common = { client, goTo }
  const Page = {
    overview: <OverviewPage {...common} />,
    analytics: <AnalyticsPage {...common} />,
    events: <EventsPage {...common} />,
    products: <ProductsPage {...common} />,
    billing: <BillingPage {...common} />,
    sync: <SyncPage {...common} />,
    'search-settings': <SearchSettingsPage {...common} />,
    widget: <WidgetPage {...common} />,
    support: <SupportPage {...common} />,
    settings: <SettingsPage {...common} />,
  }[page] || <OverviewPage {...common} />

  return (
    <div id="app-root" className="min-h-screen flex">
      {/* 🤖 Blu, always one tap away — knows only THIS client's data */}
      <BluAssistant client={client} onSpotlight={spotlight} />

      {/* 🎯 Blu's bouncing "here it is!" pointer */}
      {arrow && (
        <div className="fixed z-[60] pointer-events-none -translate-x-1/2"
             style={{ left: arrow.x, top: arrow.y - 58 }}>
          <div className="blu-arrow-bounce flex flex-col items-center">
            <span className="text-[11px] font-bold bg-mint text-white rounded-full
                             px-3 py-1 shadow-lg whitespace-nowrap mb-0.5">
              🤖 here it is!</span>
            <span className="text-3xl leading-none">👇</span>
          </div>
        </div>
      )}
      {/* ---------- desktop sidebar ---------- */}
      <aside className="hidden md:flex flex-col w-56 shrink-0 border-r border-white/10
                        bg-black/20 p-4 sticky top-0 h-screen overflow-y-auto">
        <div className="mb-1 flex justify-center"><BrandLogo size={34} /></div>
        <div className="text-[10px] text-mist tracking-widest mb-5 text-center">CLIENT PORTAL</div>
        <nav className="flex-1 space-y-1">
          {NAV.map(n => (
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
            <span className={`w-8 h-4.5 h-[18px] rounded-full relative transition
                  ${theme === 'dark' ? 'bg-mint' : 'bg-black/25'}`}>
              <span className={`absolute top-[2px] w-3.5 h-3.5 rounded-full bg-white
                    shadow transition-all ${theme === 'dark' ? 'left-4' : 'left-[2px]'}`} />
            </span>
          </button>
          <div className="flex items-center gap-2.5 px-1">
            <div className="w-8 h-8 rounded-full bg-mint/20 border border-mint/40
                            flex items-center justify-center text-mint font-extrabold text-sm">
              {(client.name || client.client_id || '?')[0]?.toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="text-xs font-semibold truncate">{client.name || client.client_id}</div>
              <button onClick={signOut} className="text-[11px] text-mist hover:text-coral
                                                   transition">sign out →</button>
            </div>
          </div>
        </div>
      </aside>

      {/* ---------- main ---------- */}
      <main className="flex-1 min-w-0 p-4 md:p-6 pb-24 md:pb-6">
        {/* mobile top bar */}
        <div className="md:hidden flex items-center justify-between mb-4">
          <BrandLogo size={26} />
          <div className="flex items-center gap-3">
            <button onClick={flipTheme} className="text-base">
              {theme === 'dark' ? '🌙' : '☀️'}</button>
            <button onClick={signOut} className="text-xs text-mist">sign out →</button>
          </div>
        </div>
        {Page}
        <div className="text-center text-[10px] text-mist/60 mt-10">
          Venue Marketplace · Client Portal · your data only, always
        </div>
      </main>

      {/* ---------- mobile bottom nav ---------- */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-black/70 backdrop-blur
                      border-t border-white/10 flex justify-around py-2">
        {NAV.filter(n => MOBILE_NAV.includes(n.id)).map(n => (
          <button key={n.id} onClick={() => goTo(n.id)}
                  className={`flex flex-col items-center gap-0.5 px-1 py-1 rounded-lg text-[10px]
                              transition ${page === n.id ? 'text-mint' : 'text-mist'}`}>
            <span className="text-base">{n.icon}</span>{n.label.split(' ')[0]}
          </button>
        ))}
        <button onClick={() => goTo('settings')}
                className={`flex flex-col items-center gap-0.5 px-1 py-1 rounded-lg text-[10px]
                            ${page === 'settings' ? 'text-mint' : 'text-mist'}`}>
          <span className="text-base">⚙️</span>More
        </button>
      </nav>
    </div>
  )
}
