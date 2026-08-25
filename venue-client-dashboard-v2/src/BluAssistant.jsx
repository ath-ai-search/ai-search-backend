// =====================================================================
// 💬 BLU ASSISTANT — the same robot, living INSIDE the portal.
// Floating button → chat panel. He answers ONLY about THIS client's
// own dashboard (the backend grounds him on their session data alone).
// =====================================================================
import { useEffect, useRef, useState } from 'react'
import { askAssistant } from './api.js'
import BluBot from './blu.jsx'

const SUGGESTIONS = [
  'How is my shop doing today?',
  'What did search earn me this month?',
  'Which searches found nothing?',
  'What is my AI cost this month?',
]

export default function BluAssistant({ client, onSpotlight }) {
  const [open, setOpen] = useState(false)
  const [msgs, setMsgs] = useState([])          // {role:'user'|'blu', text}
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) },
            [msgs, busy, open])

  const ask = async (q) => {
    const question = (q || input).trim()
    if (!question || busy) return
    setInput('')
    setMsgs(m => [...m, { role: 'user', text: question }])
    setBusy(true)
    try {
      // send the recent turns so blu remembers the conversation
      const history = msgs.slice(-8).map(m => ({
        who: m.role === 'user' ? 'user' : 'blu', text: m.text }))
      const r = await askAssistant(question, history)
      setMsgs(m => [...m, { role: 'blu', text: r.answer,
                            followups: r.followups || [],
                            actions: r.actions || [],
                            goto: r.goto || null, find: r.find || null }])
    } catch (ex) {
      setMsgs(m => [...m, { role: 'blu',
        text: String(ex.message || 'Something went wrong — try again in a moment.') }])
    }
    setBusy(false)
  }

  return (
    <>
      {/* floating Blu button — above the mobile bottom nav */}
      {!open && (
        <button onClick={() => setOpen(true)} aria-label="Ask blu"
                className="fixed z-50 right-4 bottom-20 md:bottom-6 md:right-6 group">
          <div className="relative">
            <div className="absolute inset-0 rounded-full bg-mint/30 blur-xl scale-110
                            group-hover:scale-125 transition" />
            <div className="relative bg-white border border-mint/40 rounded-full p-2
                            shadow-[0_12px_30px_-8px_rgba(109,74,255,0.45)]
                            group-hover:-translate-y-1 transition">
              <BluBot size={window.innerWidth < 768 ? 44 : 68} follow={false} />
            </div>
            <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-mint
                             border-2 border-white pulse-dot" />
          </div>
        </button>
      )}

      {/* chat panel */}
      {open && (
        <div className="fixed z-50 right-2 left-2 bottom-20 md:left-auto md:right-6
                        md:bottom-6 md:w-[460px] chat-pop">
          <div className="bg-white border border-mint/25 rounded-2xl overflow-hidden
                          shadow-[0_24px_70px_-18px_rgba(109,74,255,0.45)] flex flex-col
                          h-[70vh] md:h-[600px] md:max-h-[80vh]">
            {/* header */}
            <div className="flex items-center gap-3 px-4 py-3 bg-gradient-to-r
                            from-mint/10 to-teal/10 border-b border-mint/15">
              <BluBot size={56} follow={false} mood={busy ? 'think' : 'happy'} />
              <div className="flex-1 min-w-0">
                <div className="text-base font-extrabold text-foam">blu</div>
                <div className="text-xs text-mist truncate">
                  your dashboard assistant · {client?.name || client?.client_id} only
                </div>
              </div>
              <button onClick={() => setOpen(false)}
                      className="text-mist hover:text-foam transition text-xl p-2 min-w-[40px]
                                 min-h-[40px] flex items-center justify-center">✕</button>
            </div>

            {/* messages */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
              {msgs.length === 0 && (
                <div>
                  <div className="text-sm text-foam bg-mint/10 border border-mint/20
                                  rounded-2xl rounded-tl-md px-3 py-2 inline-block">
                    Hi {client?.name || ''} 👋 I know everything about YOUR dashboard —
                    sales, searches, costs. Ask me anything!
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {SUGGESTIONS.map(s => (
                      <button key={s} onClick={() => ask(s)}
                              className="text-[11px] px-2.5 py-1.5 rounded-full bg-white
                                         border border-mint/30 text-teal hover:bg-mint/10
                                         transition">{s}</button>
                    ))}
                  </div>
                </div>
              )}
              {msgs.map((m, i) => (
                <div key={i} className={m.role === 'user' ? 'text-right' : ''}>
                  <div className={`text-sm px-3 py-2 inline-block max-w-[85%] text-left
                       whitespace-pre-wrap break-words ${m.role === 'user'
                         ? 'bg-mint text-white rounded-2xl rounded-br-md'
                         : 'bg-mint/10 text-foam border border-mint/20 rounded-2xl rounded-tl-md'}`}>
                    {m.text}
                  </div>
                  {/* ⚡ actions blu really performed for this client */}
                  {m.role === 'blu' && (m.actions || []).length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {m.actions.map((a, j) => (
                        <span key={j} className="text-[11px] px-2.5 py-1 rounded-full
                              bg-emerald-500/15 border border-emerald-500/40
                              text-emerald-600 font-semibold">{a}</span>
                      ))}
                    </div>
                  )}
                  {/* 🎯 Blu can take you to the data he is talking about */}
                  {m.role === 'blu' && m.goto && (
                    <div className="mt-2">
                      <button onClick={() => {
                                onSpotlight?.(m.goto, m.find)
                                if (window.innerWidth < 768) setOpen(false)
                              }}
                              className="text-[11px] px-3 py-1.5 rounded-full bg-mint
                                         text-white font-bold hover:bg-teal transition
                                         shadow-[0_6px_16px_-6px_rgba(109,74,255,0.6)]">
                        👉 Show me — it's on {m.goto.replace('-', ' ')}
                      </button>
                    </div>
                  )}
                  {/* 💡 related next questions — only under Blu's LATEST answer */}
                  {m.role === 'blu' && i === msgs.length - 1 && !busy &&
                    (m.followups || []).length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {m.followups.map(f => (
                        <button key={f} onClick={() => ask(f)}
                                className="text-[11px] px-2.5 py-1.5 rounded-full bg-white
                                           border border-mint/30 text-teal hover:bg-mint/10
                                           transition text-left">{f}</button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {busy && (
                <div className="text-mint text-lg leading-none px-2">
                  <span className="typing-dot">●</span>
                  <span className="typing-dot">●</span>
                  <span className="typing-dot">●</span>
                </div>
              )}
              <div ref={endRef} />
            </div>

            {/* input */}
            <form onSubmit={e => { e.preventDefault(); ask() }}
                  className="flex gap-2 p-3 border-t border-mint/15 bg-white">
              <input value={input} onChange={e => setInput(e.target.value)}
                     placeholder="ask about your shop…" maxLength={500} autoFocus
                     className="flex-1 rounded-xl bg-black/25 border border-white/15 px-3.5
                                py-2.5 text-sm outline-none focus:border-mint/60 transition" />
              <button disabled={busy || !input.trim()}
                      className="rounded-xl bg-mint hover:bg-teal text-white font-bold
                                 px-5 text-base transition disabled:opacity-40">→</button>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
