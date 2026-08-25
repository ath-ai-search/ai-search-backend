// =====================================================================
// ⚙️ SETTINGS — account info + self-service password change
// =====================================================================
import { useEffect, useState } from 'react'
import { getMe, changePassword } from '../api.js'
import { Panel, PageTitle, Badge, Skeleton, ago, ExplainCard } from '../ui.jsx'

export default function SettingsPage() {
  const [me, setMe] = useState(null)
  const [oldPw, setOldPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [newPw2, setNewPw2] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)     // {ok, text}

  useEffect(() => {
    let alive = true
    getMe().then(x => alive && setMe(x)).catch(() => {})
    return () => { alive = false }
  }, [])

  const submit = async (e) => {
    e.preventDefault()
    if (newPw.length < 10) { setMsg({ ok: false, text: 'New password needs at least 10 characters' }); return }
    if (newPw !== newPw2) { setMsg({ ok: false, text: 'New passwords do not match' }); return }
    setBusy(true); setMsg(null)
    try {
      await changePassword(oldPw, newPw)
      setOldPw(''); setNewPw(''); setNewPw2('')
      setMsg({ ok: true, text: 'Password changed ✓ — use it from your next sign-in' })
    } catch (ex) {
      setMsg({ ok: false, text: String(ex.message || 'failed') })
    }
    setBusy(false)
  }

  return (
    <div>
      <PageTitle icon="⚙️" title="Settings" desc="Your account, your keys, your password." />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Panel title="🏢 Account">
          {me === null ? <Skeleton h={120} /> : (
            <div className="space-y-2.5 text-sm">
              <div className="flex justify-between"><span className="text-mist">Company</span>
                <span className="font-semibold">{me.name}</span></div>
              <div className="flex justify-between"><span className="text-mist">Client ID</span>
                <code className="text-mint text-xs">{me.client_id}</code></div>
              <div className="flex justify-between"><span className="text-mist">Account status</span>
                <Badge tone="mint">● Active</Badge></div>
              <div className="flex justify-between"><span className="text-mist">Member since</span>
                <span className="text-xs">{String(me.created_at || '').slice(0, 10) || '—'}</span></div>
              <div className="flex justify-between"><span className="text-mist">Products live</span>
                <span>{(me.products || 0).toLocaleString()}</span></div>
              <div className="flex justify-between"><span className="text-mist">Last search on your site</span>
                <span className="text-xs">{ago(me.doctor?.last_search_at)}</span></div>
              <div className="flex justify-between"><span className="text-mist">Last product sync</span>
                <span className="text-xs">{me.doctor?.last_sync
                  ? `${(me.doctor.last_sync.indexed || 0).toLocaleString()} products · ${ago(me.doctor.last_sync.finished_at)}`
                  : 'none yet'}</span></div>
              <div className="flex justify-between items-center">
                <span className="text-mist">Site token</span>
                <span className="flex items-center gap-2">
                  <code className="text-xs text-mint">{String(me.site_token || '').slice(0, 4)}••••</code>
                  <button onClick={() => navigator.clipboard?.writeText(me.site_token || '')}
                          className="text-[11px] px-2 py-0.5 rounded-lg bg-mint/15 border
                                     border-mint/30 text-mint hover:bg-mint/25 transition">
                    copy</button>
                </span>
              </div>
              <div className="flex justify-between"><span className="text-mist">Portal address</span>
                <a href="https://venuemarketplace.xyz/portal/" className="text-xs text-mint hover:underline">
                  venuemarketplace.xyz/portal</a></div>
            </div>
          )}
        </Panel>

        <Panel title="🔑 Change portal password">
          <form onSubmit={submit} className="space-y-3">
            <input type="password" value={oldPw} onChange={e => setOldPw(e.target.value)}
                   placeholder="Current password" autoComplete="current-password"
                   className="w-full rounded-xl bg-black/25 border border-white/15 px-3 py-2.5
                              text-sm outline-none focus:border-mint/60 transition" />
            <input type="password" value={newPw} onChange={e => setNewPw(e.target.value)}
                   placeholder="New password (10+ characters)" autoComplete="new-password"
                   className="w-full rounded-xl bg-black/25 border border-white/15 px-3 py-2.5
                              text-sm outline-none focus:border-mint/60 transition" />
            <input type="password" value={newPw2} onChange={e => setNewPw2(e.target.value)}
                   placeholder="New password again" autoComplete="new-password"
                   className="w-full rounded-xl bg-black/25 border border-white/15 px-3 py-2.5
                              text-sm outline-none focus:border-mint/60 transition" />
            {msg && (
              <div className={`text-xs rounded-lg px-3 py-2 border ${msg.ok
                ? 'text-mint bg-mint/10 border-mint/30'
                : 'text-coral bg-coral/10 border-coral/30'}`}>{msg.text}</div>
            )}
            <button disabled={busy}
                    className="w-full rounded-xl bg-mint/90 hover:bg-mint text-white
                               font-bold py-2.5 text-sm transition disabled:opacity-50">
              {busy ? 'Changing…' : 'Change password'}</button>
          </form>
        </Panel>
      </div>

      {/* 📈 plan usage + session safety */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
        <Panel title="📦 Your products">
          {me === null ? <Skeleton h={140} /> : (
            <div className="flex items-center gap-6 py-4">
              <div className="w-24 h-24 shrink-0 rounded-2xl bg-mint/10 border
                              border-mint/25 flex items-center justify-center text-4xl">
                🛍️
              </div>
              <div>
                <div className="text-4xl font-extrabold text-mint tabular leading-none">
                  {(me?.products || 0).toLocaleString()}</div>
                <div className="text-sm text-mist mt-2">
                  products live in your AI search</div>
              </div>
            </div>
          )}
        </Panel>
        <Panel title="🛡️ Your session, protected">
          <div className="space-y-2.5 text-sm py-1">
            {[['⏱️', 'Sign-ins last 8 hours, then a fresh login is needed'],
              ['🔐', 'Password stored only as a strong hash — nobody can read it'],
              ['🚫', 'Wrong password 8 times → login pauses for 10 minutes'],
              ['👁️', 'You can only ever see YOUR data — enforced on every request']]
              .map(([ic, t]) => (
              <div key={t} className="flex items-start gap-2.5">
                <span>{ic}</span><span className="text-xs text-mist pt-0.5">{t}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <ExplainCard icon="⚙️"
        lines={[
          'This page is your account home — your company, your plan, your password.',
          'Change your password any time; it works on the next sign-in.',
        ]}
        example={'Want a new portal password? Type the current one, then the new one twice — it works on your very next sign-in.'} />
    </div>
  )
}
