// ☁️ AZURE page — what our cloud is actually doing right now.
// Two sources: Azure itself (VM facts via IMDS) and the machine's own
// Linux counters (CPU / memory / disk) — the ones that actually warn you
// before something breaks.
import { useEffect, useState } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { Stat, PageTitle, Panel, TT } from '../ui.jsx'
import { getAzureInfo } from '../api.js'
import AzureCloud3D from '../AzureCloud3D.jsx'

const COLORS = ['#38bdf8', '#a78bfa', '#34d399', '#fbbf24', '#f472b6', '#60a5fa', '#f87171']

// a coloured bar for CPU / memory / disk (green -> amber -> red)
function Meter({ label, percent, sub }) {
  const p = Math.max(0, Math.min(100, percent ?? 0))
  const color = p >= 90 ? 'bg-red-400' : p >= 75 ? 'bg-amber-400' : 'bg-emerald-400'
  const text  = p >= 90 ? 'text-red-300' : p >= 75 ? 'text-amber-300' : 'text-emerald-300'
  return (
    <div className="rounded-2xl bg-white/5 border border-white/10 p-4">
      <div className="flex justify-between items-baseline mb-2">
        <span className="text-xs uppercase tracking-wider text-slate-400">{label}</span>
        <span className={`text-lg font-bold ${text}`}>{percent == null ? '—' : `${p}%`}</span>
      </div>
      <div className="h-2 rounded-full bg-white/10 overflow-hidden">
        <div className={`h-full ${color} transition-all duration-700`} style={{ width: `${p}%` }} />
      </div>
      {sub && <div className="text-[11px] text-slate-500 mt-2">{sub}</div>}
    </div>
  )
}

export default function AzurePage() {
  const [d, setD] = useState(null)

  useEffect(() => {
    let alive = true
    const load = () => getAzureInfo().then(x => alive && setD(x)).catch(() => {})
    load()
    const id = setInterval(load, 5000)          // machine stats are live
    return () => { alive = false; clearInterval(id) }
  }, [])

  const inst    = d?.instances?.[0]
  const machine = d?.machine || {}
  const cost    = d?.cost || {}
  const sg      = d?.security_groups?.[0]
  const stack   = d?.stack || {}
  const live    = String(d?.source || '').startsWith('live')

  const costPie = (cost.items || [])
    .filter(i => i.monthly > 0)
    .map(i => ({ name: `${i.service} $${i.monthly.toFixed(2)}`, value: i.monthly }))

  return (
    <div>
      <PageTitle icon="☁️" title="Azure"
                 desc="Live view of the cloud: what we run, how healthy it is, how it is protected, and what it costs." />

      {/* ---------- top row: 3D live view + the server stats ---------- */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        {/* 3D scene — the VM as a particle globe, one satellite per service,
            green/red by REAL probe status. Stacks on top on mobile. */}
        <div className="relative rounded-2xl bg-white/5 border border-white/10 overflow-hidden h-56 sm:h-64 lg:h-auto lg:min-h-[16rem]">
          <AzureCloud3D services={d?.services || []} />
          <div className="absolute top-3 left-4 text-xs uppercase tracking-wider text-slate-400">
            ☁️ Azure VM — live
          </div>
          <div className="absolute bottom-3 left-4 text-xs text-slate-400">
            {(d?.services || []).filter(s => s.up).length}/{(d?.services || []).length || 5} services 🟢 ·
            each orbiting dot = one service
          </div>
        </div>

        <div className="lg:col-span-2 grid grid-cols-1 xs:grid-cols-2 gap-4">
          <Stat label="Virtual Machine" value={inst?.type || '—'}
                sub={inst ? `${machine.cores || '?'} vCPU · ${machine.memory?.total_gb ?? '?'} GB RAM` : 'loading…'} accent="text-cyan-400" />
          <Stat label="Running since" value={machine.uptime_hours != null ? `${(machine.uptime_hours / 24).toFixed(1)} d` : '—'}
                sub={machine.uptime_hours != null ? `OS uptime ${machine.uptime_hours} h` : ''} accent="text-violet-400" />
          <Stat label="Public address" value={d?.addresses?.[0]?.ip || inst?.public_ip || '—'}
                sub={d?.https?.active ? `🔒 ${d.https.domain}` : 'static IP — never changes'} accent="text-emerald-400" />
          <Stat label="Azure cost / month" value={`$${(cost.monthly_total ?? 0).toFixed(2)}`}
                sub={`≈ $${(cost.daily_estimate ?? 0).toFixed(2)} per day`} accent="text-amber-400" />
        </div>
      </div>

      {/* ---------- domain + HTTPS certificate, checked for real ---------- */}
      {d?.https?.domain && (
        <Panel title="🔒 Domain & HTTPS — the certificate, checked live" className="mb-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Stat label="Domain" value={d.https.domain}
                  sub={d.https.active ? 'HTTPS active — http:// auto-redirects' : '⚠️ certificate not answering'}
                  accent={d.https.active ? 'text-emerald-400' : 'text-red-400'} />
            <Stat label="Certificate expires" value={d.https.expires || '—'}
                  sub={d.https.days_left != null ? `${d.https.days_left} days left · certbot renews it automatically` : (d.https.error || '')}
                  accent={d.https.days_left == null ? 'text-slate-400'
                          : d.https.days_left > 30 ? 'text-emerald-400'
                          : d.https.days_left > 10 ? 'text-amber-400' : 'text-red-400'} />
            <div className="rounded-2xl bg-white/5 border border-white/10 p-4">
              <div className="text-xs uppercase tracking-wider text-slate-400 mb-2">Live URLs</div>
              <div className="text-sm space-y-1">
                {['docs', 'shop/docs', 'health'].map(path => (
                  <div key={path}>
                    <a className="text-cyan-300 hover:underline" target="_blank" rel="noreferrer"
                       href={`https://${d.https.domain}/${path}`}>
                      https://{d.https.domain}/{path}
                    </a>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Panel>
      )}

      {/* ---------- the platform stack: what actually runs inside the VM ---------- */}
      <Panel title="🧱 The platform inside this VM — every piece, live-checked" className="mb-4">
        <div className="text-xs text-slate-500 mb-3">
          The cloud console can only show you the machine. This shows what runs INSIDE it:
          three database containers and two APIs. Each row is probed directly, so a green
          dot means it really answered just now.
          <span className="text-emerald-400 ml-1">All databases are bound to localhost — unreachable from the internet.</span>
        </div>
        <div className="overflow-auto">
          <table className="w-full text-sm min-w-[34rem]">
            <thead>
              <tr className="text-[11px] uppercase tracking-wider text-slate-500 border-b border-white/10">
                <th className="text-left py-1.5">Component</th>
                <th className="text-left py-1.5">What it does</th>
                <th className="text-left py-1.5">Image / process</th>
                <th className="text-right py-1.5">Port</th>
                <th className="text-right py-1.5">Status</th>
              </tr>
            </thead>
            <tbody>
              {(d?.services || []).map(s => (
                <tr key={s.port} className="border-b border-white/5">
                  <td className="py-1.5 font-semibold text-cyan-300 whitespace-nowrap">
                    {s.kind === 'container' ? '🐳 ' : '⚙️ '}{s.name}
                  </td>
                  <td className="py-1.5 text-slate-400 text-xs">{s.role}</td>
                  <td className="py-1.5 text-slate-500 text-[11px] font-mono">{s.image}</td>
                  <td className="py-1.5 text-right text-slate-400 text-xs whitespace-nowrap">127.0.0.1:{s.port}</td>
                  <td className="py-1.5 text-right whitespace-nowrap">
                    {s.up
                      ? <span className="text-emerald-400">🟢 running</span>
                      : <span className="text-red-400">🔴 down</span>}
                  </td>
                </tr>
              ))}
              {!d?.services?.length && <tr><td className="text-slate-500 py-2">loading…</td></tr>}
            </tbody>
          </table>
        </div>
        {stack.embedding_model && (
          <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
            <Chip>📦 {d?.index?.products != null ? d.index.products.toLocaleString() : '—'} products stored</Chip>
            <Chip>OpenSearch {stack.opensearch_version || '—'}</Chip>
            <Chip>Python {stack.python || '—'}</Chip>
            <Chip>index “{stack.index}”</Chip>
            <Chip>{stack.embedding_model} · {stack.embedding_dims} dims</Chip>
            <Chip>kernel {stack.kernel || '—'}</Chip>
          </div>
        )}
      </Panel>

      {/* ---------- machine health: the early-warning signs ---------- */}
      <Panel title="💓 Server health — read from the machine itself" className="mb-4">
        <div className="text-xs text-slate-500 mb-3">
          Azure does not warn you about these. A full database disk is the most common way a
          search server dies, so watch that bar.
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Meter label="CPU" percent={machine.cpu_percent}
                 sub={machine.load_1m != null ? `load ${machine.load_1m} on ${machine.cores || '?'} cores` : ''} />
          <Meter label="Memory" percent={machine.memory?.percent}
                 sub={machine.memory ? `${machine.memory.used_gb} / ${machine.memory.total_gb} GB used` : ''} />
          {(machine.disks || []).map(dk => (
            <Meter key={dk.path} label={dk.name} percent={dk.percent}
                   sub={`${dk.used_gb} / ${dk.total_gb} GB used · ${dk.free_gb} GB free`} />
          ))}
        </div>
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        {/* ---------- what we run ---------- */}
        <Panel title="🖥️ What we run in Azure">
          <div className="text-xs mb-3">
            {live
              ? <span className="rounded-full bg-emerald-500/15 text-emerald-300 px-2 py-0.5">🟢 live from Azure</span>
              : <span className="rounded-full bg-amber-500/15 text-amber-300 px-2 py-0.5">{d?.source || 'loading…'}</span>}
            {d?.resource_group && <span className="ml-2 text-slate-600">resource group {d.resource_group} · {d.region}</span>}
          </div>

          {inst && (
            <div className="text-sm space-y-1 mb-4">
              <Line isAnimationActive={false} k="Virtual Machine" v={inst.name} />
              <Line isAnimationActive={false} k="Size" v={`${inst.type} · ${inst.state}`} />
              <Line isAnimationActive={false} k="vCPU / RAM" v={`${machine.cores || '?'} vCPU · ${machine.memory?.total_gb ?? '?'} GB`} />
              <Line isAnimationActive={false} k="Region" v={inst.region || d?.region} />
              <Line isAnimationActive={false} k="Availability zone" v={d?.zone} />
              <Line isAnimationActive={false} k="Resource group" v={inst.resource_group || d?.resource_group} />
              <Line isAnimationActive={false} k="Subscription" v={inst.subscription} />
              <Line isAnimationActive={false} k="OS" v={`${inst.os || ''} — ${inst.ami || ''}`} />
              <Line isAnimationActive={false} k="Image version" v={inst.os_version} />
              <Line isAnimationActive={false} k="Admin user" v={inst.admin_user} />
              <Line isAnimationActive={false} k="Private IP" v={inst.private_ip} />
              <Line isAnimationActive={false} k="Public IP" v={inst.public_ip} />
              <Line isAnimationActive={false} k="Cloud environment" v={d?.environment} />
              <Line isAnimationActive={false} k="Metadata protected" v={inst.imdsv2 ? '✅ yes (IMDS header required)' : '⚠️ no'} />
              {d?.scale_set && <Line isAnimationActive={false} k="Scale set" v={d.scale_set} />}
            </div>
          )}

          <div className="text-xs uppercase tracking-wider text-slate-500 mb-2">Disks</div>
          <table className="w-full text-sm min-w-[22rem]">
            <tbody>
              {(d?.volumes || []).map(v => (
                <tr key={v.id} className="border-b border-white/5">
                  <td className="py-1.5 text-slate-300">{v.name}</td>
                  <td className="py-1.5 text-slate-500 text-xs">{v.type} · {v.device || ''}</td>
                  <td className="py-1.5 text-right text-cyan-300">{v.size_gb} GB</td>
                  <td className="py-1.5 text-right text-xs">
                    {v.encrypted ? <span className="text-emerald-400">🔒 encrypted</span>
                                 : <span className="text-amber-400">not encrypted</span>}
                  </td>
                </tr>
              ))}
              {!d?.volumes?.length && <tr><td className="text-slate-500 text-sm py-2">loading…</td></tr>}
            </tbody>
          </table>
        </Panel>

        {/* ---------- how it is protected ---------- */}
        <Panel title="🔒 How the server is protected">
          {sg ? (
            <>
              <div className="text-xs text-slate-500 mb-3">{sg.name}</div>

              <div className="text-xs uppercase tracking-wider text-emerald-400 mb-2">Open — what may come IN</div>
              <table className="w-full text-sm mb-4">
                <tbody>
                  {sg.inbound.map((r, i) => (
                    <tr key={i} className="border-b border-white/5">
                      <td className="py-1.5 text-cyan-300 font-semibold whitespace-nowrap">
                        {r.protocol} {r.ports}
                        {r.live === 'open' && <span className="ml-2 text-emerald-400 text-xs">🟢 open</span>}
                        {r.live === 'closed' && <span className="ml-2 text-red-400 text-xs">🔴 closed</span>}
                      </td>
                      <td className="py-1.5 text-slate-500 text-xs">{r.why || r.from}</td>
                      <td className="py-1.5 text-right text-slate-400 text-xs">{r.from}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="text-xs uppercase tracking-wider text-red-300 mb-2">Closed — unreachable from the internet</div>
              <ul className="text-sm text-slate-400 space-y-1">
                {sg.closed_ports.map((c, i) => <li key={i}>🚫 {c}</li>)}
              </ul>

              <div className="mt-4 text-xs text-slate-500">
                Outbound: {sg.outbound.map(o => `${o.protocol} ${o.ports}`).join(', ') || '—'}
                <span className="ml-1">(needed for OpenAI, GitHub and Ubuntu updates)</span>
                {sg.note && <div className="mt-1 text-slate-600">{sg.note}</div>}
              </div>
            </>
          ) : <div className="text-sm text-slate-500">loading firewall rules…</div>}
        </Panel>
      </div>

      {/* ---------- cost split ---------- */}
      <Panel title="💵 What each Azure service costs" className="h-[26rem] md:h-96">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 h-full">
          <ResponsiveContainer width="100%" height="90%">
            <PieChart>
              <Pie isAnimationActive={false} data={costPie} dataKey="value" nameKey="name" innerRadius={55} outerRadius={95} paddingAngle={3}>
                {costPie.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip {...TT} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>

          <div className="overflow-auto">
            <table className="w-full text-sm min-w-[22rem]">
              <tbody>
                {(cost.items || []).map((i, k) => (
                  <tr key={k} className="border-b border-white/5">
                    <td className="py-1.5 font-semibold text-cyan-300 whitespace-nowrap">{i.service}</td>
                    <td className="py-1.5 text-slate-500 text-xs">{i.detail}</td>
                    <td className="py-1.5 text-right text-slate-200">
                      {i.monthly > 0 ? `$${i.monthly.toFixed(2)}` : <span className="text-emerald-400">free</span>}
                    </td>
                  </tr>
                ))}
                <tr>
                  <td className="py-2 font-bold text-slate-200" colSpan={2}>TOTAL per month</td>
                  <td className="py-2 text-right font-bold text-amber-300">${(cost.monthly_total ?? 0).toFixed(2)}</td>
                </tr>
              </tbody>
            </table>
            <div className="text-[11px] text-slate-600 mt-2">{cost.source}</div>
          </div>
        </div>
      </Panel>
    </div>
  )
}

function Line({ k, v }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-slate-500">{k}</span>
      <span className="text-slate-200 font-mono text-xs truncate">{v ?? '—'}</span>
    </div>
  )
}

function Chip({ children }) {
  return (
    <span className="rounded-full bg-white/5 border border-white/10 px-2 py-0.5 text-slate-400">
      {children}
    </span>
  )
}
