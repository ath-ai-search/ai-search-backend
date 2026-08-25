// =====================================================================
// 👥 CLIENTS page — onboard & manage tenants (ADMIN — only us)
// =====================================================================
// Add a client here -> their key + site token are generated, their
// dashboard tab appears in the switcher BY ITSELF, their APIs work.
// The API key is shown exactly ONCE (stored only as a hash) — copy it
// into the client's integration document immediately.
// =====================================================================
import { useEffect, useState } from 'react'
import { Stat, PageTitle, Panel, fmtMoney } from '../ui.jsx'
import {
  getClients, getAdminOverview, createClient, updateClient,
  rotateClientKey, deleteClient, setPortalPassword,
} from '../api.js'

export default function ClientsPage() {
  const [data, setData] = useState(null)
  const [overview, setOverview] = useState(null)
  const [form, setForm] = useState({ client_id: '', name: '' })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [fieldErr, setFieldErr] = useState({})   // which form fields are missing
  const [secret, setSecret] = useState(null)   // the ONCE-visible key reveal

  const load = () => {
    getClients().then(setData).catch(() => {})
    getAdminOverview().then(setOverview).catch(() => {})
  }
  useEffect(() => {
    load()
    const id = setInterval(load, 10000)
    return () => clearInterval(id)
  }, [])

  const clients = data?.clients || []
  const rows = overview?.clients || []
  const rowFor = id => rows.find(r => r.client_id === id) || {}

  const onCreate = async (e) => {
    e.preventDefault()
    // tell the user exactly WHICH field is missing (instead of a dead button)
    const missing = {
      client_id: !form.client_id.trim(),
      name: !form.name.trim(),
    }
    setFieldErr(missing)
    if (missing.client_id || missing.name) {
      setErr('Please fill the highlighted field(s) before creating the client.')
      return
    }
    setErr(''); setBusy(true)
    try {
      const res = await createClient({ client_id: form.client_id.trim(), name: form.name.trim() })
      setSecret(res)                      // show key + site token ONCE
      setForm({ client_id: '', name: '' })
      setFieldErr({})
      load()
    } catch (ex) { setErr(String(ex.message || ex)) }
    setBusy(false)
  }

  const onRotate = async (id) => {
    if (!window.confirm(`Generate a NEW key for "${id}"? The old key stops working instantly.`)) return
    try { setSecret(await rotateClientKey(id)); load() } catch (ex) { setErr(String(ex.message || ex)) }
  }

  const onPortalPw = async (id) => {
    const pw = window.prompt(
      `Set the CLIENT-PORTAL password for "${id}" (minimum 10 characters).
` +
      'The client signs in at portal.venuemarketplace.xyz with their client id + this password.')
    if (pw === null) return
    if ((pw || '').length < 10) { setErr('Portal password needs at least 10 characters.'); return }
    try {
      await setPortalPassword(id, pw)
      setErr('')
      window.alert(`Portal password set for "${id}" — share it with the client safely.`)
    } catch (ex) { setErr(String(ex.message || ex)) }
  }

  const onPause = async (c) => {
    const to = c.status === 'active' ? 'paused' : 'active'
    try { await updateClient(c.client_id, { status: to }); load() } catch (ex) { setErr(String(ex.message || ex)) }
  }

  const onDelete = async (id) => {
    const pw = window.prompt(
      `\u26a0\ufe0f DELETE CLIENT "${id}" \u2014 THIS REMOVES EVERYTHING:\n` +
      `their products, their AI vectors, their fields, their billing history.\n\n` +
      `This cannot be undone. Enter the DELETE PASSWORD to continue:`)
    if (pw === null) return                       // cancelled
    try {
      await deleteClient(id, true, pw)
      setErr('')
      load()
    } catch (ex) { setErr(String(ex.message || ex)) }
  }

  return (
    <div>
      <PageTitle icon="👥" title="Clients"
                 desc="Onboard and manage tenants. Add a client — their dashboard, key and APIs exist immediately. Only we see this page." />

      {/* ---------- the ONCE-visible secret reveal ---------- */}
      {secret && (
        <Panel title="🔑 SAVE THESE NOW — shown only once (stored as a hash)" className="mb-4 border-amber-500/40">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-xs uppercase tracking-wider text-slate-400 mb-1">Client</div>
              <div className="font-mono text-cyan-300">{secret.client_id}</div>
            </div>
            {secret.site_token && (
              <div>
                <div className="text-xs uppercase tracking-wider text-slate-400 mb-1">Site token (for the widget)</div>
                <div className="font-mono text-emerald-300 select-all">{secret.site_token}</div>
              </div>
            )}
            <div className="md:col-span-2">
              <div className="text-xs uppercase tracking-wider text-slate-400 mb-1">API key (X-API-Key)</div>
              <div className="font-mono text-amber-300 break-all select-all rounded-lg bg-black/30 border border-amber-500/30 p-3">
                {secret.api_key}
              </div>
            </div>
          </div>
          <div className="flex items-center justify-between mt-3">
            <div className="text-xs text-amber-400">⚠️ Copy the key into the client's integration document + the private credentials sheet NOW.</div>
            <button onClick={() => setSecret(null)}
                    className="text-xs rounded-lg bg-white/10 px-3 py-1.5 hover:bg-white/20 transition">I saved it — hide</button>
          </div>
        </Panel>
      )}

      {err && <div className="mb-4 text-sm text-red-400 card-in">⚠️ {err}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        {/* ---------- onboard form ---------- */}
        <Panel title="➕ Onboard a new client">
          <form onSubmit={onCreate} className="space-y-3">
            <div>
              <label className="text-xs uppercase tracking-wider text-slate-400">client id</label>
              <input value={form.client_id}
                     onChange={e => { setForm(f => ({ ...f, client_id: e.target.value })); setFieldErr(fe => ({ ...fe, client_id: false })) }}
                     placeholder="e.g. client2  (a-z, 0-9, dash)"
                     className={`mt-1 w-full rounded-lg bg-white/5 border px-3 py-2 text-sm outline-none transition ${
                       fieldErr.client_id ? 'border-red-400/70 focus:border-red-400' : 'border-white/15 focus:border-blue-400/60'}`} />
              {fieldErr.client_id && <div className="text-[11px] text-red-400 mt-1">⚠️ Client id is required</div>}
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider text-slate-400">display name</label>
              <input value={form.name}
                     onChange={e => { setForm(f => ({ ...f, name: e.target.value })); setFieldErr(fe => ({ ...fe, name: false })) }}
                     placeholder="e.g. Acme Store GmbH"
                     className={`mt-1 w-full rounded-lg bg-white/5 border px-3 py-2 text-sm outline-none transition ${
                       fieldErr.name ? 'border-red-400/70 focus:border-red-400' : 'border-white/15 focus:border-blue-400/60'}`} />
              {fieldErr.name && <div className="text-[11px] text-red-400 mt-1">⚠️ Display name is required</div>}
            </div>
            <button disabled={busy}
                    className="w-full rounded-lg bg-blue-600/40 border border-blue-400/50 text-white py-2 text-sm font-semibold hover:bg-blue-500/60 hover:border-blue-300/70 transition disabled:opacity-40">
              {busy ? 'creating…' : 'Create client (generates key + site token)'}
            </button>
            <div className="text-[11px] text-slate-600">
              Their switcher tab, dashboard, index and APIs appear automatically — no code change, no redeploy.
            </div>
          </form>
        </Panel>

        {/* ---------- client list ---------- */}
        <Panel title={`📋 All clients (${clients.length})`} className="lg:col-span-2 overflow-auto">
          <table className="w-full text-sm min-w-[34rem]">
            <thead>
              <tr className="text-slate-400 text-xs border-b border-white/10">
                <th className="text-left py-2 pr-3">Client</th>
                <th className="text-left pr-3">Status</th>
                <th className="text-right pr-3">Products</th>
                <th className="text-right pr-3">Fields</th>
                <th className="text-right pr-3">AI cost</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {clients.map(c => {
                const r = rowFor(c.client_id)
                return (
                  <tr key={c.client_id} className="border-b border-white/5 hover:bg-white/5 transition">
                    <td className="py-2 pr-3">
                      <div className="font-semibold text-slate-200">{c.name}</div>
                      <div className="text-[11px] font-mono text-slate-500">{c.client_id} · site: {c.site_token}</div>
                    </td>
                    <td className="pr-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        c.status === 'active' ? 'bg-emerald-500/15 text-emerald-300' : 'bg-amber-500/15 text-amber-300'}`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="text-right pr-3 tabular text-cyan-300">{c.products ?? '—'}</td>
                    <td className="text-right pr-3 tabular text-slate-300">{r.fields ?? '—'}</td>
                    <td className="text-right pr-3 tabular text-amber-300">{r.runs_cost != null ? fmtMoney(r.runs_cost) : '—'}</td>
                    <td className="text-right whitespace-nowrap">
                      <button onClick={() => onRotate(c.client_id)} title="new key"
                              className="text-xs rounded bg-white/5 px-2 py-1 hover:bg-white/15 transition mr-1">🔑</button>
                      <button onClick={() => onPortalPw(c.client_id)} title="set client-portal password"
                              className="text-xs rounded bg-white/5 px-2 py-1 hover:bg-white/15 transition mr-1">🛡️</button>
                      {c.client_id !== 'default' && (
                        <>
                          <button onClick={() => onPause(c)} title={c.status === 'active' ? 'pause' : 'resume'}
                                  className="text-xs rounded bg-white/5 px-2 py-1 hover:bg-white/15 transition mr-1">
                            {c.status === 'active' ? '⏸️' : '▶️'}
                          </button>
                          <button onClick={() => onDelete(c.client_id)} title="remove"
                                  className="text-xs rounded bg-rose-500/10 text-rose-300 px-2 py-1 hover:bg-rose-500/25 transition">🗑️</button>
                        </>
                      )}
                    </td>
                  </tr>
                )
              })}
              {!clients.length && (
                <tr><td colSpan="6" className="text-slate-500 text-sm py-4 text-center">loading clients…</td></tr>
              )}
            </tbody>
          </table>
          <div className="text-[11px] text-slate-600 mt-3">
            🔑 = new key (old dies instantly) · ⏸️ = pause (their key + storefront go quiet, data kept) ·
            🗑️ = remove from the platform. The <span className="font-mono">default</span> client is the original tenant.
          </div>
        </Panel>
      </div>
    </div>
  )
}
