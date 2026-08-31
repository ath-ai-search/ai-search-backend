// =====================================================================
// 🚪 SIGN-IN — Blu v2 greets you: glossy 3D robot, glowing eyes that
// follow your mouse, typewriter welcome. He closes his eyes while you
// type your password 🙈 and shakes his head sadly on a wrong one.
// =====================================================================
import { useEffect, useRef, useState } from 'react'
import { login, setSession } from '../api.js'
import { Starfield } from '../three3d.jsx'
import BluBot from '../blu.jsx'
import BrandLogo from '../BrandLogo.jsx'

const GREETINGS = [
  "Hi! I'm blu 👋",
  'Welcome to Venue Marketplace!',
  'I watch your shop search 24/7',
  'Sign in — your world is waiting',
]

function SpeechBubble({ mood }) {
  const [text, setText] = useState('')
  const [idx, setIdx] = useState(0)

  useEffect(() => {
    if (mood !== 'happy') return   // moods speak instantly, no typing
    let i = 0, t
    const full = GREETINGS[idx]
    const tick = () => {
      i += 1
      setText(full.slice(0, i))
      t = i < full.length
        ? setTimeout(tick, 45)
        : setTimeout(() => setIdx(x => (x + 1) % GREETINGS.length), 2300)
    }
    t = setTimeout(tick, 300)
    return () => clearTimeout(t)
  }, [idx, mood])

  const line = mood === 'shy' ? "I won't look — promise! 🙈"
             : mood === 'sad' ? "Hmm, that didn't match… try again!"
             : text
  return (
    <div className="relative bg-white border border-mint/30 rounded-2xl px-4 py-2
                    text-sm text-foam shadow-[0_8px_24px_-10px_rgba(109,74,255,0.35)]
                    min-h-[38px] min-w-[190px] text-center">
      {line}{mood === 'happy' && <span className="blu-caret text-mint">▍</span>}
      <div className="absolute left-1/2 -bottom-1.5 -translate-x-1/2 w-3 h-3 bg-white
                      border-b border-r border-mint/30 rotate-45" />
    </div>
  )
}

export default function LoginPage({ onSignedIn }) {
  const [clientId, setClientId] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [mood, setMood] = useState('happy')
  const [shake, setShake] = useState(false)
  const [focusId, setFocusId] = useState(null)

  const submit = async (e) => {
    e.preventDefault()
    if (!clientId.trim() || !password) {
      setErr('Please fill in both fields'); return
    }
    setBusy(true); setErr('')
    try {
      const r = await login(clientId.trim(), password)
      setSession(r.token, r.client)
      onSignedIn(r.client)
    } catch (ex) {
      setErr(String(ex.message || 'Sign-in failed'))
      setMood('sad'); setShake(true)
      setTimeout(() => setShake(false), 600)
      setTimeout(() => setMood('happy'), 2600)
    }
    setBusy(false)
  }

  return (
    <div className="min-h-screen relative flex items-center justify-center p-4 overflow-hidden">
      <Starfield />
      {/* 🟣 brand — top-left corner of the page */}
      <div className="absolute top-5 left-6 z-10 select-none">
        <BrandLogo size={30} />
        <div className="text-[10px] text-mist mt-1 tracking-[0.25em]">CLIENT PORTAL</div>
      </div>
      <div className="relative w-full max-w-md card-in">
        <div className="flex flex-col items-center mb-5 select-none">
          <SpeechBubble mood={mood} />
          <div className="mt-3">
            <BluBot mood={mood} shake={shake} size={150} />
          </div>
        </div>

        <form onSubmit={submit}
              className="bg-tide/80 backdrop-blur border border-white/10 rounded-card p-8
                         shadow-[0_20px_60px_-20px_rgba(109,74,255,0.30)]">
          <label className="block text-[11px] uppercase tracking-wider text-mist mb-1">
            Client ID</label>
          <input id="login-client" value={clientId}
                 onChange={e => { setClientId(e.target.value); setErr('') }}
                 onFocus={() => setFocusId('login-client')}
                 onBlur={() => setFocusId(f => (f === 'login-client' ? null : f))}
                 autoFocus autoComplete="username" placeholder="venue"
                 className="w-full rounded-xl bg-black/25 border border-white/15 px-4 py-3
                            text-base outline-none focus:border-mint/60 transition mb-5" />
          <label className="block text-[11px] uppercase tracking-wider text-mist mb-1">
            Portal password</label>
          <input id="login-pass" type="password" value={password}
                 onChange={e => { setPassword(e.target.value); setErr('') }}
                 onFocus={() => { setMood('shy'); setFocusId('login-pass') }}
                 onBlur={() => { setMood(m => (m === 'shy' ? 'happy' : m))
                                 setFocusId(f => (f === 'login-pass' ? null : f)) }}
                 autoComplete="current-password" placeholder="••••••••••"
                 className="w-full rounded-xl bg-black/25 border border-white/15 px-4 py-3
                            text-base outline-none focus:border-mint/60 transition" />
          {err && (
            <div className="mt-3 text-xs text-coral bg-coral/10 border border-coral/30
                            rounded-lg px-3 py-2">⚠️ {err}</div>
          )}
          <button disabled={busy}
                  className="mt-5 w-full rounded-xl bg-mint hover:bg-teal text-white
                             font-extrabold py-3 text-base transition disabled:opacity-50">
            {busy ? 'Signing in…' : 'Enter your dashboard →'}
          </button>
          <div className="text-[11px] text-mist text-center mt-4">
            No account? Your provider creates it for you.
          </div>
        </form>

        {/* what waits inside */}
        <div className="flex justify-center gap-2 mt-5 flex-wrap">
          {['🔎 AI search', '🛰️ Live activity', '💰 Real revenue', '🤖 blu assistant']
            .map(f => (
            <span key={f} className="text-[11px] px-3 py-1.5 rounded-full bg-white/60
                  border border-mint/25 text-teal font-semibold backdrop-blur">{f}</span>
          ))}
        </div>
      </div>

    </div>
  )
}
