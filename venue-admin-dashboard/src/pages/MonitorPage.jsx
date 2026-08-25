// =====================================================================
// 📡 LIVE MONITOR — new page (Azure edition feature)
// =====================================================================
// Watches the server BREATHE: every 5 seconds it samples the machine
// (CPU, memory, service probes, our own network latency to the server)
// and draws rolling 5-minute graphs. Nothing is stored — the history
// lives in the browser tab; open the page and it starts recording.
// =====================================================================
import { useEffect, useRef, useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid,
} from 'recharts'
import { Stat, PageTitle, Panel, TT } from '../ui.jsx'
import { getAzureInfo } from '../api.js'

const MAX_POINTS = 60          // 60 samples x 5s = 5 minutes of history

export default function MonitorPage() {
  const [d, setD] = useState(null)
  const [history, setHistory] = useState([])
  const alive = useRef(true)

  useEffect(() => {
    alive.current = true
    const sample = async () => {
      const t0 = performance.now()
      try {
        const x = await getAzureInfo()
        const ms = Math.round(performance.now() - t0)
        if (!alive.current) return
        setD(x)
        const m = x?.machine || {}
        const now = new Date()
        setHistory(h => [...h, {
          t: now.toLocaleTimeString([], { minute: '2-digit', second: '2-digit' }),
          cpu: m.cpu_percent ?? null,
          mem: m.memory?.percent ?? null,
          latency: ms,
        }].slice(-MAX_POINTS))
      } catch { /* server unreachable — the gap in the graph tells the story */ }
    }
    sample()
    const id = setInterval(sample, 5000)
    return () => { alive.current = false; clearInterval(id) }
  }, [])

  const machine = d?.machine || {}
  const services = d?.services || []
  const upCount = services.filter(s => s.up).length
  const last = history[history.length - 1] || {}
  const disks = machine.disks || []

  return (
    <div>
      <PageTitle icon="📡" title="Live Monitor"
                 desc="The server's heartbeat, recorded while you watch — CPU, memory, service probes and network latency, sampled every 5 seconds." />

      {/* ---------- now numbers ---------- */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <Stat label="Services live" value={`${upCount}/${services.length || 5}`}
              sub="each probed right now" accent={upCount === (services.length || 5) ? 'text-emerald-400' : 'text-red-400'} />
        <Stat label="CPU now" value={machine.cpu_percent != null ? `${machine.cpu_percent}%` : '—'}
              sub={machine.load_1m != null ? `load ${machine.load_1m} on ${machine.cores} cores` : ''} accent="text-cyan-400" />
        <Stat label="Memory now" value={machine.memory?.percent != null ? `${machine.memory.percent}%` : '—'}
              sub={machine.memory ? `${machine.memory.used_gb} / ${machine.memory.total_gb} GB` : ''} accent="text-violet-400" />
        <Stat label="Your latency" value={last.latency != null ? `${last.latency} ms` : '—'}
              sub="browser → server → back" accent="text-amber-400" />
      </div>

      {/* ---------- rolling CPU + memory ---------- */}
      <Panel title="💓 CPU & memory — last 5 minutes" className="mb-4 h-72">
        <ResponsiveContainer width="100%" height="88%">
          <AreaChart data={history} margin={{ top: 6, right: 8, left: -18, bottom: 0 }}>
            <defs>
              <linearGradient id="gCpu" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#5f95ff" stopOpacity={0.25} />
                <stop offset="100%" stopColor="#5f95ff" stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id="gMem" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#9d7bff" stopOpacity={0.25} />
                <stop offset="100%" stopColor="#9d7bff" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="t" tickLine={false} axisLine={false} minTickGap={40} />
            <YAxis domain={[0, 100]} unit="%" tickLine={false} axisLine={false} width={52} />
            <Tooltip {...TT} />
            <Area type="linear" dataKey="cpu" name="CPU %" stroke="#5f95ff" strokeWidth={2}
                  fill="url(#gCpu)" isAnimationActive={false} connectNulls />
            <Area type="linear" dataKey="mem" name="Memory %" stroke="#9d7bff" strokeWidth={2}
                  fill="url(#gMem)" isAnimationActive={false} connectNulls />
          </AreaChart>
        </ResponsiveContainer>
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        {/* ---------- latency graph ---------- */}
        <Panel title="🌐 Network latency — you to the server" className="h-64">
          <ResponsiveContainer width="100%" height="86%">
            <AreaChart data={history} margin={{ top: 6, right: 8, left: -14, bottom: 0 }}>
              <defs>
                <linearGradient id="gLat" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f5c04e" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="#f5c04e" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="t" tickLine={false} axisLine={false} minTickGap={40} />
              <YAxis unit="ms" tickLine={false} axisLine={false} width={52} />
              <Tooltip {...TT} />
              <Area type="linear" dataKey="latency" name="round-trip ms" stroke="#f5c04e"
                    strokeWidth={2} fill="url(#gLat)" isAnimationActive={false} connectNulls />
            </AreaChart>
          </ResponsiveContainer>
        </Panel>

        {/* ---------- live service tiles ---------- */}
        <Panel title="🧩 Services — probed live" className="h-64 overflow-auto">
          <div className="grid grid-cols-1 xs:grid-cols-2 gap-2">
            {services.map(s => (
              <div key={s.port}
                   className={`rounded-xl border p-3 transition ${
                     s.up ? 'bg-emerald-500/5 border-emerald-500/20'
                          : 'bg-red-500/10 border-red-500/40'}`}>
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full pulse-dot ${s.up ? 'bg-emerald-400' : 'bg-red-400'}`} />
                  <span className="text-sm font-semibold">{s.kind === 'container' ? '🐳' : '⚙️'} {s.name}</span>
                </div>
                <div className="text-[11px] text-slate-500 mt-1">{s.role}</div>
                <div className="text-[11px] font-mono text-slate-400 mt-1">127.0.0.1:{s.port}</div>
              </div>
            ))}
            {!services.length && <div className="text-sm text-slate-500">loading…</div>}
          </div>
        </Panel>
      </div>

      {/* ---------- disks + certificate ---------- */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {disks.map(dk => (
          <Stat key={dk.path} label={dk.name} value={dk.percent != null ? `${dk.percent}%` : '—'}
                sub={`${dk.used_gb} / ${dk.total_gb} GB used · ${dk.free_gb} GB free`}
                accent={dk.percent >= 90 ? 'text-red-400' : dk.percent >= 75 ? 'text-amber-400' : 'text-emerald-400'} />
        ))}
        {d?.https?.days_left != null && (
          <Stat label="HTTPS certificate" value={`${d.https.days_left} days`}
                sub={`expires ${d.https.expires} · renews automatically`}
                accent={d.https.days_left > 30 ? 'text-emerald-400' : d.https.days_left > 10 ? 'text-amber-400' : 'text-red-400'} />
        )}
      </div>
    </div>
  )
}
