// =====================================================================
// 🎫 TICKETS page — every client's support tickets in one inbox (ADMIN)
// =====================================================================
// Clients write tickets in THEIR portal; we answer here. A reply lands
// in their portal instantly as "support". Statuses:
//   open = waiting on US · pending = waiting on the client · resolved
// =====================================================================
import { useEffect, useState } from 'react'
import { PageTitle, Panel } from '../ui.jsx'
import { getAdminTickets, adminTicketReply } from '../api.js'

const STATUS_LOOK = {
  open:     'bg-rose-500/15 text-rose-300 border-rose-500/30',
  pending:  'bg-amber-500/15 text-amber-300 border-amber-500/30',
  resolved: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
}
const PRIO_LOOK = {
  high: 'text-rose-300', normal: 'text-slate-300', low: 'text-slate-400',
}
const ago = (iso) => {
  if (!iso) return '—'
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  if (s < 3600) return `${Math.max(1, Math.round(s / 60))}m ago`
  if (s < 86400) return `${Math.round(s / 3600)}h ago`
  return `${Math.round(s / 86400)}d ago`
}

export default function TicketsPage() {
  const [status, setStatus] = useState('')
  const [data, setData] = useState(null)
  const [sel, setSel] = useState(null)          // selected ticket id
  const [reply, setReply] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const load = () => getAdminTickets(status).then(setData).catch(() => {})
  useEffect(() => {
    setData(null); load()
    const id = setInterval(load, 12000)
    return () => clearInterval(id)
  }, [status])

  const tickets = data?.tickets || []
  const current = tickets.find(t => t.id === sel)

  const act = async (id, body) => {
    setBusy(true); setErr('')
    try { await adminTicketReply(id, body); setReply(''); await load() }
    catch (ex) { setErr(String(ex.message || ex)) }
    setBusy(false)
  }

  return (
    <div>
      <PageTitle icon="🎫" title="Support tickets"
                 desc="Every client's tickets in one inbox — replies appear in their portal instantly." />

      <div className="flex gap-2 flex-wrap mb-4 items-center">
        {[['', '🌐 All'], ['open', '🔴 Open (need us)'],
          ['pending', '🟡 Pending (client)'], ['resolved', '✅ Resolved']].map(([id, label]) => (
          <button key={id} onClick={() => { setStatus(id); setSel(null) }}
                  className={`px-3.5 py-2 rounded-xl text-sm border transition ${
                    status === id ? 'bg-sky-500/20 border-sky-400/50 text-sky-100'
                                  : 'bg-white/5 border-white/10 text-slate-400 hover:bg-white/10'}`}>
            {label}
          </button>
        ))}
        <span className="ml-auto text-xs text-slate-400">
          {data ? `${data.open_count} waiting on us` : '…'}</span>
      </div>
      {err && <div className="text-xs text-rose-300 mb-3">⚠️ {err}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* inbox */}
        <Panel title="📥 Inbox" className="lg:col-span-2">
          {data === null ? <div className="text-sm text-slate-400 py-3">loading…</div>
            : tickets.length ? (
            <div className="space-y-1.5 max-h-[560px] overflow-y-auto pr-1">
              {tickets.map(t => (
                <button key={t.id} onClick={() => setSel(t.id)}
                        className={`w-full text-left rounded-xl border px-3 py-2.5 transition ${
                          sel === t.id ? 'bg-sky-500/15 border-sky-400/40'
                                       : 'bg-white/[0.03] border-white/5 hover:bg-white/5'}`}>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-white/10
                                     text-slate-200 font-mono shrink-0">{t.client_id}</span>
                    <span className="text-sm truncate flex-1">{t.subject}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-1.5 text-[11px]">
                    <span className={`px-2 py-0.5 rounded-full border ${
                      STATUS_LOOK[t.status] || STATUS_LOOK.open}`}>{t.status}</span>
                    <span className={PRIO_LOOK[t.priority] || ''}>{t.priority}</span>
                    <span className="text-slate-500 ml-auto">{ago(t.updated_at)}</span>
                  </div>
                </button>
              ))}
            </div>
          ) : <div className="text-sm text-slate-400 py-3">
                no tickets here — clients are happy 🎉</div>}
        </Panel>

        {/* thread */}
        <Panel title={current ? `💬 ${current.subject}` : '💬 Pick a ticket'}
               className="lg:col-span-3">
          {current ? (
            <div className="flex flex-col h-[560px]">
              <div className="text-[11px] text-slate-400 mb-2">
                <span className="font-mono text-slate-200">{current.client_id}</span>
                {' · '}{current.priority} priority · opened {ago(current.created_at)}
              </div>
              <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
                {(current.messages || []).map((m, i) => (
                  <div key={i} className={m.who === 'support' ? 'text-right' : ''}>
                    <div className={`inline-block max-w-[85%] text-left text-sm px-3 py-2
                         rounded-2xl whitespace-pre-wrap ${m.who === 'support'
                           ? 'bg-sky-500/20 border border-sky-400/30 rounded-br-md'
                           : 'bg-white/5 border border-white/10 rounded-tl-md'}`}>
                      <div className="text-[10px] text-slate-400 mb-0.5">
                        {m.who === 'support' ? '🛠️ us' : `👤 ${current.client_id}`} · {ago(m.at)}
                      </div>
                      {m.text}
                    </div>
                  </div>
                ))}
              </div>
              <div className="pt-3 border-t border-white/10 mt-3">
                <textarea value={reply} onChange={e => setReply(e.target.value)}
                          rows={2} placeholder="write the answer — the client sees it in their portal…"
                          className="w-full rounded-xl bg-black/25 border border-white/15 px-3
                                     py-2 text-sm outline-none focus:border-sky-400/60 transition" />
                <div className="flex gap-2 mt-2">
                  <button disabled={busy || !reply.trim()}
                          onClick={() => act(current.id, { message: reply })}
                          className="rounded-xl bg-sky-500/80 hover:bg-sky-500 text-white
                                     font-bold px-4 py-2 text-sm transition disabled:opacity-40">
                    Send reply</button>
                  {current.status !== 'resolved' ? (
                    <button disabled={busy}
                            onClick={() => act(current.id,
                              { message: reply.trim() || null, resolve: true })}
                            className="rounded-xl bg-emerald-500/20 border border-emerald-400/40
                                       text-emerald-300 px-4 py-2 text-sm transition
                                       hover:bg-emerald-500/30 disabled:opacity-40">
                      ✅ Resolve</button>
                  ) : (
                    <button disabled={busy}
                            onClick={() => act(current.id, { reopen: true })}
                            className="rounded-xl bg-white/5 border border-white/15 text-slate-300
                                       px-4 py-2 text-sm transition hover:bg-white/10
                                       disabled:opacity-40">
                      ↩️ Reopen</button>
                  )}
                </div>
              </div>
            </div>
          ) : <div className="text-sm text-slate-400 py-6 text-center">
                select a ticket on the left to read and answer it</div>}
        </Panel>
      </div>
    </div>
  )
}
