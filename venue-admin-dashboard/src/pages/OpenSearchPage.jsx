// OpenSearch page — cluster + index details, with bar + pie charts
import { useEffect, useState } from 'react'
import {
  BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer,
  XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from 'recharts'
import { Stat, PageTitle, Panel, TT, DONUT, fmtBytes } from '../ui.jsx'

export default function OpenSearchPage({ stats, osInfo }) {
  // 📱 recharts props can't react to CSS breakpoints — track "phone width" here
  // so the pie legend can stack below the chart instead of overlapping it
  const [narrow, setNarrow] = useState(() => window.matchMedia('(max-width: 639px)').matches)
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 639px)')
    const onChange = (e) => setNarrow(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  const s = stats || {}
  const o = osInfo || {}
  // 🐞 BUG FIX: read categories from OpenSearch itself (o.categories) —
  // always real, survives API restarts. Fall back to live-run stats only.
  const catSource = (o.categories && Object.keys(o.categories).length ? o.categories : s.categories) || {}
  const cats = Object.entries(catSource)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  // 📊 A real catalogue has 50+ categories. Drawing them all makes both
  // charts unreadable (rotated labels overlap, the legend covers the pie).
  // So: the bar chart shows the TOP 12 as horizontal bars (names stay
  // readable), and the pie groups the small ones into a single "Other".
  const TOP_BARS = 12
  const TOP_SLICES = 8
  const barData = cats.slice(0, TOP_BARS).slice().reverse()   // biggest at the top

  const bigSlices = cats.slice(0, TOP_SLICES)
  const restCount = cats.length - bigSlices.length
  const restTotal = cats.slice(TOP_SLICES).reduce((a, c) => a + c.value, 0)
  const pieData = restTotal > 0
    ? [...bigSlices, { name: `Other (${restCount} categories)`, value: restTotal }]
    : bigSlices

  const shortName = (n, max = 22) => (n.length > max ? n.slice(0, max - 1) + '…' : n)

  const statusColor = o.status === 'green' ? 'text-emerald-400'
    : o.status === 'yellow' ? 'text-amber-400' : 'text-red-400'

  return (
    <div>
      <PageTitle icon="🔍" title="OpenSearch" desc="Our search database — stores every product + its AI vector, and runs the search." />

      <div className="grid grid-cols-1 xs:grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <Stat label="Status" value={(o.status || '-').toUpperCase()} accent={statusColor} sub={`${o.nodes || 0} node(s)`} />
        <Stat label="Documents" value={o.docs || 0} sub="products indexed" accent="text-cyan-400" />
        <Stat label="Index size" value={fmtBytes(o.size_bytes)} sub={`index: ${o.index || 'products'}`} accent="text-violet-400" />
        <Stat label="Active shards" value={o.active_shards || 0} sub="data pieces" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        {/* horizontal bars: category names stay readable, no rotated text */}
        <Panel title={`📊 Top ${Math.min(TOP_BARS, cats.length)} categories`} className="h-80 md:h-96">
          <div className="text-[11px] text-slate-500 -mt-1 mb-1">
            {cats.length} categories in total · biggest first
          </div>
          <ResponsiveContainer width="100%" height="88%">
            <BarChart data={barData} layout="vertical" margin={{ top: 2, right: 26, left: 4, bottom: 2 }}>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" stroke="#64748b" tick={{ fontSize: 10 }} allowDecimals={false} />
              <YAxis type="category" dataKey="name" width={narrow ? 96 : 128} stroke="#64748b"
                     tick={{ fontSize: 10 }} tickFormatter={(n) => shortName(n, narrow ? 14 : 22)} interval={0} />
              <Tooltip {...TT} />
              <Bar isAnimationActive={false} dataKey="value" name="Products" radius={[0, 4, 4, 0]} barSize={13}>
                {barData.map((_, i) => <Cell key={i} fill={DONUT[i % DONUT.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Panel>

        {/* pie: only the big slices, everything small grouped into "Other" */}
        <Panel title="🍩 Share of the catalogue" className="h-80 md:h-96">
          <div className="text-[11px] text-slate-500 -mt-1 mb-1">
            top {Math.min(TOP_SLICES, cats.length)} categories{restCount > 0 ? `, rest grouped as "Other"` : ''}
          </div>
          <ResponsiveContainer width="100%" height="88%">
            <PieChart margin={{ top: 0, right: 4, bottom: 0, left: 4 }}>
              <Pie isAnimationActive={false} data={pieData} dataKey="value" nameKey="name"
                   cx={narrow ? '50%' : '34%'} cy="50%"
                   innerRadius={narrow ? 32 : 40} outerRadius={narrow ? 55 : 72} paddingAngle={2} stroke="none">
                {pieData.map((_, i) => <Cell key={i} fill={DONUT[i % DONUT.length]} />)}
              </Pie>
              <Tooltip {...TT} />
              {/* phones: legend under the chart (a right-hand legend overlaps the slices) */}
              <Legend layout={narrow ? 'horizontal' : 'vertical'}
                      align={narrow ? 'center' : 'right'}
                      verticalAlign={narrow ? 'bottom' : 'middle'}
                      wrapperStyle={narrow ? { fontSize: 10 } : { fontSize: 10, lineHeight: '15px', maxWidth: '52%' }}
                      formatter={(v) => shortName(String(v))} />
            </PieChart>
          </ResponsiveContainer>
        </Panel>
      </div>

      <Panel title="ℹ️ About this index">
        <div className="text-sm text-slate-400 space-y-1.5">
          <div>• Each product is stored with all its fields <b className="text-slate-200">plus a 3072-number AI embedding</b> (text-embedding-3-large).</div>
          <div>• Search uses <b className="text-slate-200">kNN vector search</b> on the embedding — it finds products by <b>meaning</b>, not just keywords.</div>
          <div>• Status <b className="text-amber-400">yellow</b> is normal for a single-node dev cluster (replica shards stay unassigned — harmless).</div>
        </div>
      </Panel>
    </div>
  )
}
