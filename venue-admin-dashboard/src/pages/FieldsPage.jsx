// Fields page — what the client registered via the Fields API (API 1)
import { useEffect, useState } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { Stat, PageTitle, Panel, TT, DONUT } from '../ui.jsx'
// client-aware data layer — NEVER raw fetch (it would bypass the switcher)
import { getFields } from '../api.js'

// same rule the backend uses: these fields don't go into the AI meaning text
const inAiText = (f) =>
  (f.os_type === 'text' || f.os_type === 'keyword') &&
  !f.name.toLowerCase().endsWith('url') &&
  !['sku', 'image', 'slug'].includes(f.name.toLowerCase())

export default function FieldsPage({ selClient }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    let alive = true
    const load = () => getFields().then(d => alive && setData(d)).catch(() => {})
    setData(null)                               // clear instantly on client switch
    load()
    const id = setInterval(load, 4000)          // live: updates when a client registers
    return () => { alive = false; clearInterval(id) }
  }, [selClient])

  const reg = data?.registered
  const fields = data?.fields || []
  const aiFields = fields.filter(inAiText)
  const typeCounts = {}
  fields.forEach(f => { typeCounts[f.type] = (typeCounts[f.type] || 0) + 1 })
  const donut = Object.entries(typeCounts).map(([name, value]) => ({ name, value }))
  const when = data?.registered_at ? new Date(data.registered_at * 1000).toLocaleString() : '—'

  return (
    <div>
      <PageTitle icon="🗂️" title="Fields"
                 desc="What the client registered through the Fields API — our index is built DYNAMICALLY from these (no hardcoded names)." />

      {!reg && (
        <Panel title="⏳ Waiting for the client">
          <div className="text-sm text-slate-400">
            No fields registered yet. When the client's connector calls
            <span className="text-cyan-300 font-mono"> POST /fields/register</span>, everything appears here live.
          </div>
        </Panel>
      )}

      {reg && (
        <>
          <div className="grid grid-cols-1 xs:grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <Stat label="Registered fields" value={fields.length} sub={`client: ${data.client_id}`} accent="text-cyan-400" />
            <Stat label="ID field" value={data.id_field} sub="their unique product key" accent="text-amber-400" />
            <Stat label="Used for AI meaning" value={aiFields.length} sub="text fields → embedding" accent="text-violet-400" />
            <Stat label="Registered on" value={when.split(',')[0]} sub={when.split(',')[1] || ''} accent="text-emerald-400" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
            <Panel title="📊 Field types" className="h-60 md:h-72">
              <ResponsiveContainer width="100%" height="88%">
                <PieChart>
                  <Pie isAnimationActive={false} data={donut} dataKey="value" nameKey="name" innerRadius={42} outerRadius={80} paddingAngle={2} stroke="none">
                    {donut.map((_, i) => <Cell key={i} fill={DONUT[i % DONUT.length]} />)}
                  </Pie>
                  <Tooltip {...TT} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            </Panel>

            <Panel title="🗂️ All registered fields" className="lg:col-span-2">
              <div className="overflow-x-auto max-h-72 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-slate-900">
                    <tr className="text-slate-400 text-xs border-b border-white/10">
                      <th className="text-left py-2 pl-2">Field name (client's)</th>
                      <th className="text-left">Their type</th>
                      <th className="text-left">Stored as</th>
                      <th className="text-center">In AI meaning?</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fields.map(f => (
                      <tr key={f.name} className="border-b border-white/5">
                        <td className="py-1.5 pl-2 font-mono text-xs text-slate-200">
                          {f.name}{f.name === data.id_field && <span className="ml-2 text-[10px] bg-amber-500/20 text-amber-300 rounded-full px-2 py-0.5">⭐ ID</span>}
                        </td>
                        <td className="text-slate-400 text-xs">{f.type}</td>
                        <td className="text-slate-400 text-xs">{f.os_type}</td>
                        <td className="text-center text-xs">{inAiText(f) ? <span className="text-violet-300">🤖 yes</span> : <span className="text-slate-600">—</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          </div>

          <Panel title="🤖 Added by US automatically">
            <div className="flex items-center gap-3 text-sm">
              <span className="font-mono text-xs bg-violet-500/15 border border-violet-500/30 text-violet-300 rounded-full px-3 py-1.5">embedding · knn_vector · 3072 numbers</span>
              <span className="text-slate-400">the AI "meaning" — the client never sends this, our API creates it for every product</span>
            </div>
          </Panel>
        </>
      )}
    </div>
  )
}
