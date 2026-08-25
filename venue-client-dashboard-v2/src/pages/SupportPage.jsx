// =====================================================================
// 🎫 SUPPORT — tickets with chat-style threads (create, reply, resolve)
// =====================================================================
import { useEffect, useState } from 'react'
import { getTickets, createTicket, replyTicket, resolveTicket } from '../api.js'
import { Panel, PageTitle, Badge, Skeleton, ago, ExplainCard } from '../ui.jsx'

export default function SupportPage() {
  const [tickets, setTickets] = useState(null)
  const [open, setOpen] = useState(null)          // opened ticket object
  const [showNew, setShowNew] = useState(false)
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [priority, setPriority] = useState('normal')
  const [reply, setReply] = useState('')
  const [busy, setBusy] = useState(false)

  const load = () => getTickets().then(d => {
    setTickets(d.tickets || [])
    if (open) setOpen((d.tickets || []).find(t => t.id === open.id) || null)
  }).catch(() => setTickets([]))
  useEffect(() => { load() }, [])

  const submitNew = async (e) => {
    e.preventDefault()
    if (subject.trim().length < 3 || !message.trim()) return
    setBusy(true)
    try {
      await createTicket(subject.trim(), message.trim(), priority)
      setShowNew(false); setSubject(''); setMessage('')
      load()
    } catch { /* stays open */ }
    setBusy(false)
  }

  const sendReply = async (e) => {
    e.preventDefault()
    if (!reply.trim() || !open) return
    setBusy(true)
    try { await replyTicket(open.id, reply.trim()); setReply(''); load() } catch {}
    setBusy(false)
  }

  const markResolved = async () => {
    if (!open) return
    try { await resolveTicket(open.id); load() } catch {}
  }

  return (
    <div>
      <PageTitle icon="🎫" title="Support"
                 desc="Something wrong or a question? We answer here." />

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <Panel className="lg:col-span-2" title="Your tickets"
               right={<button onClick={() => setShowNew(true)}
                              className="text-xs px-3 py-1.5 rounded-lg bg-mint/20 border
                                         border-mint/40 text-mint hover:bg-mint/30 transition
                                         font-semibold">+ New ticket</button>}>
          {tickets === null ? <Skeleton h={140} /> : tickets.length ? (
            <div className="space-y-2 max-h-[420px] overflow-y-auto">
              {tickets.map(t => (
                <button key={t.id} onClick={() => setOpen(t)}
                        className={`w-full text-left rounded-lg px-3 py-2.5 border transition ${
                          open?.id === t.id
                            ? 'bg-mint/10 border-mint/40'
                            : 'bg-white/[0.03] border-white/5 hover:bg-white/[0.06]'}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-semibold truncate">{t.subject}</span>
                    <Badge tone={t.status === 'resolved' ? 'mint' : 'sand'}>{t.status}</Badge>
                  </div>
                  <div className="text-[11px] text-mist mt-0.5">
                    {t.messages?.length || 1} message{(t.messages?.length || 1) > 1 ? 's' : ''} ·
                    updated {ago(t.updated_at)}</div>
                </button>
              ))}
            </div>
          ) : <div className="text-sm text-mist py-3">no tickets — everything running smooth 🌊</div>}
        </Panel>

        <Panel className="lg:col-span-3"
               title={open ? <span className="truncate">💬 {open.subject}</span> : '💬 Pick a ticket'}
               right={open && open.status !== 'resolved' &&
                 <button onClick={markResolved}
                         className="text-xs text-mint hover:underline">✓ mark resolved</button>}>
          {open ? (
            <div className="flex flex-col h-[420px]">
              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {(open.messages || []).map((m, i) => (
                  <div key={i} className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
                    m.who === 'client'
                      ? 'ml-auto bg-mint/15 border border-mint/30'
                      : 'bg-white/[0.05] border border-white/10'}`}>
                    <div className="text-[10px] text-mist mb-0.5">
                      {m.who === 'client' ? 'You' : 'Support'} · {ago(m.at)}</div>
                    <div className="whitespace-pre-wrap break-words">{m.text}</div>
                  </div>
                ))}
              </div>
              <form onSubmit={sendReply} className="flex gap-2 mt-3">
                <input value={reply} onChange={e => setReply(e.target.value)}
                       placeholder="write a reply…"
                       className="flex-1 rounded-xl bg-black/25 border border-white/15 px-3
                                  py-2 text-sm outline-none focus:border-mint/60 transition" />
                <button disabled={busy}
                        className="rounded-xl bg-mint/90 hover:bg-mint text-white font-bold
                                   px-4 text-sm transition disabled:opacity-50">Send</button>
              </form>
            </div>
          ) : <div className="text-sm text-mist py-4">
                select a ticket on the left, or create a new one</div>}
        </Panel>
      </div>

      {/* new ticket modal */}
      {showNew && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
             onClick={() => setShowNew(false)}>
          <form onSubmit={submitNew} onClick={e => e.stopPropagation()}
                className="bg-tide border border-white/10 rounded-card p-5 w-full max-w-md card-in">
            <div className="text-sm font-bold mb-3">🎫 New support ticket</div>
            <input value={subject} onChange={e => setSubject(e.target.value)}
                   placeholder="Subject" autoFocus
                   className="w-full rounded-xl bg-black/25 border border-white/15 px-3 py-2.5
                              text-sm outline-none focus:border-mint/60 transition mb-3" />
            <textarea value={message} onChange={e => setMessage(e.target.value)}
                      placeholder="Describe the issue…" rows={4}
                      className="w-full rounded-xl bg-black/25 border border-white/15 px-3 py-2.5
                                 text-sm outline-none focus:border-mint/60 transition mb-3" />
            <div className="flex items-center justify-between">
              <select value={priority} onChange={e => setPriority(e.target.value)}
                      className="rounded-lg bg-black/25 border border-white/15 px-2 py-1.5
                                 text-xs outline-none">
                <option value="low">low priority</option>
                <option value="normal">normal priority</option>
                <option value="high">high priority</option>
              </select>
              <div className="flex gap-2">
                <button type="button" onClick={() => setShowNew(false)}
                        className="text-xs px-3 py-2 rounded-lg bg-white/5 border
                                   border-white/10 text-mist">Cancel</button>
                <button disabled={busy}
                        className="text-xs px-4 py-2 rounded-lg bg-mint/90 hover:bg-mint
                                   text-white font-bold transition disabled:opacity-50">
                  {busy ? '…' : 'Create'}</button>
              </div>
            </div>
          </form>
        </div>
      )}

      <ExplainCard icon="🎫"
        lines={[
          'Something wrong, or a question? Create a ticket — our team reads every one.',
          'Reply inside the ticket and keep the whole conversation in one place.',
          'When your problem is fixed, press resolve — done.',
        ]}
        example={'“My products are not updating after sync” → create a ticket with High priority → we fix it and answer you right here.'} />
    </div>
  )
}
