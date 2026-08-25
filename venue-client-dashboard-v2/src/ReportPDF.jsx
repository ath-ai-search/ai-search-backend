// =====================================================================
// 🧾 PDF REPORT — a clean A4 report of everything in the dashboard.
// Rendered into <body> (outside #app-root); the print stylesheet hides
// the app and shows ONLY this. The browser's "Save as PDF" does the rest.
// =====================================================================
import { createPortal } from 'react-dom'
import { fmtMoney, fmtRev } from './ui.jsx'
import { BrandMark } from './BrandLogo.jsx'

const td = { padding: '6px 10px', borderBottom: '1px solid #e2dff0', fontSize: 12,
             wordBreak: 'break-word' }
const th = { ...td, textAlign: 'left', color: '#6b6a8a', fontWeight: 600,
             textTransform: 'uppercase', fontSize: 10, letterSpacing: '0.05em' }
const num = { ...td, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }

function Kpi({ label, value, sub }) {
  return (
    <div style={{ border: '1px solid #e2dff0', borderRadius: 10, padding: '10px 12px' }}>
      <div style={{ fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.06em',
                    color: '#6b6a8a' }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 800, color: '#4a30b8' }}>{value}</div>
      {sub && <div style={{ fontSize: 10, color: '#6b6a8a' }}>{sub}</div>}
    </div>
  )
}

export default function ReportPDF({ data }) {
  if (!data) return null
  const { client, me, overview: o, billing: b, analytics: a, events: ev } = data
  const cur = b?.current || {}
  const now = new Date()

  return createPortal(
    <div className="print-report">
      {/* header */}
      <div style={{ display: 'flex', justifyContent: 'space-between',
                    borderBottom: '3px solid #6d4aff', paddingBottom: 10, marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <BrandMark size={46} />
          <div>
          <div style={{ fontSize: 22, fontWeight: 800 }}>
            <span style={{ color: '#6d4aff' }}>Venue Marketplace</span> — Search Report</div>
          <div style={{ fontSize: 12, color: '#6b6a8a' }}>
            {client?.name || client?.client_id} · plan {(me?.plan?.max_products || 0).toLocaleString()} products</div>
          </div>
        </div>
        <div style={{ textAlign: 'right', fontSize: 11, color: '#6b6a8a' }}>
          <div>Generated {now.toISOString().slice(0, 10)}</div>
          <div>Month: {b?.this_month || now.toISOString().slice(0, 7)}</div>
        </div>
      </div>

      {/* KPI grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8,
                    marginBottom: 16 }}>
        <Kpi label="Revenue from search" value={fmtRev(o?.funnel?.revenue)}
             sub={`${fmtRev(o?.revenue_total)} all time`} />
        <Kpi label="Searches" value={(o?.searches_total || 0).toLocaleString()}
             sub={`${o?.searches_today || 0} today`} />
        <Kpi label="Product clicks" value={(o?.clicks_total || 0).toLocaleString()}
             sub={`${o?.ctr_pct || 0}% of searches`} />
        <Kpi label="Orders from search" value={(o?.orders_total || 0).toLocaleString()}
             sub={`${o?.conv_pct || 0}% conversion`} />
        <Kpi label="Products live" value={(o?.products || 0).toLocaleString()} />
        <Kpi label="Avg search speed" value={`${Math.round(o?.avg_ms || 0)} ms`} />
        <Kpi label="Found nothing" value={o?.zero_count || 0} sub="searches with 0 results" />
        <Kpi label="AI cost this month" value={fmtMoney(o?.ai_cost_month)}
             sub={`${(o?.ai_tokens_month || 0).toLocaleString()} tokens`} />
      </div>

      {/* funnel */}
      <div style={{ fontSize: 13, fontWeight: 700, margin: '14px 0 6px' }}>
        🧲 Conversion funnel — this month</div>
      <div style={{ fontSize: 12, color: '#1c1733', marginBottom: 14 }}>
        {(o?.funnel?.searches || 0).toLocaleString()} searches
        &nbsp;→&nbsp; {(o?.funnel?.clicks || 0).toLocaleString()} clicks
        &nbsp;→&nbsp; {(o?.funnel?.orders || 0).toLocaleString()} orders
        &nbsp;=&nbsp; <b style={{ color: '#4a30b8' }}>{fmtRev(o?.funnel?.revenue)}</b>
      </div>

      {/* top searches */}
      <div style={{ fontSize: 13, fontWeight: 700, margin: '14px 0 6px' }}>
        🏆 Top searches</div>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 14 }}>
        <thead><tr>
          <th style={th}>Search</th><th style={{ ...th, textAlign: 'right' }}>Times</th>
          <th style={{ ...th, textAlign: 'right' }}>Click %</th>
          <th style={{ ...th, textAlign: 'right' }}>Orders</th>
          <th style={{ ...th, textAlign: 'right' }}>Revenue</th>
        </tr></thead>
        <tbody>
          {(a?.top || []).slice(0, 10).map(x => (
            <tr key={x.query}>
              <td style={td}>{x.query}</td>
              <td style={num}>{x.count}</td>
              <td style={num}>{x.ctr_pct !== undefined ? `${x.ctr_pct}%` : '—'}</td>
              <td style={num}>{x.orders ?? '—'}</td>
              <td style={num}>{x.revenue ? fmtRev(x.revenue) : '—'}</td>
            </tr>
          ))}
          {!(a?.top || []).length &&
            <tr><td style={td} colSpan={5}>no searches recorded yet</td></tr>}
        </tbody>
      </table>

      {/* found nothing */}
      {(o?.zero_top || []).length > 0 && <>
        <div style={{ fontSize: 13, fontWeight: 700, margin: '14px 0 6px' }}>
          💎 Searches that found nothing (chances to sell more)</div>
        <div style={{ fontSize: 12, marginBottom: 14 }}>
          {(o.zero_top || []).map(x => `“${x.query}” (×${x.count})`).join(' · ')}
        </div>
      </>}

      {/* billing */}
      <div style={{ fontSize: 13, fontWeight: 700, margin: '14px 0 6px' }}>
        💰 Billing — {b?.this_month}</div>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 18 }}>
        <tbody>
          <tr><td style={td}>Product indexing (AI embeddings)</td>
              <td style={num}>{fmtMoney(cur.ingest_cost)}</td>
              <td style={num}>{cur.ingest_calls || 0} products</td></tr>
          <tr><td style={td}>Search AI</td>
              <td style={num}>{fmtMoney(cur.search_cost)}</td>
              <td style={num}>{cur.search_calls || 0} AI searches</td></tr>
          <tr><td style={{ ...td, fontWeight: 800 }}>Total this month</td>
              <td style={{ ...num, fontWeight: 800, color: '#4a30b8' }}>
                {fmtMoney(cur.total_cost)}</td><td style={num} /></tr>
        </tbody>
      </table>

      {/* shopper activity snapshot */}
      {ev && (
        <>
          <div style={{ fontSize: 13, fontWeight: 700, margin: '14px 0 6px' }}>
            🛰️ Shopper activity</div>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 14 }}>
            <tbody>
              <tr>
                <td style={td}>Clicks today</td><td style={num}>{ev.today?.click || 0}</td>
                <td style={td}>Add-to-carts today</td><td style={num}>{ev.today?.add_to_cart || 0}</td>
              </tr>
              <tr>
                <td style={td}>Purchases today</td><td style={num}>{ev.today?.purchase || 0}</td>
                <td style={td}>Revenue today</td>
                <td style={{ ...num, color: '#4a30b8', fontWeight: 800 }}>
                  {fmtRev(ev.today_revenue)}</td>
              </tr>
              <tr>
                <td style={td}>All-time clicks</td><td style={num}>{ev.counts?.click || 0}</td>
                <td style={td}>All-time purchases</td><td style={num}>{ev.counts?.purchase || 0}</td>
              </tr>
            </tbody>
          </table>
        </>
      )}

      {/* month by month */}
      {(b?.months || []).length > 0 && (
        <>
          <div style={{ fontSize: 13, fontWeight: 700, margin: '14px 0 6px' }}>
            📊 Cost month by month</div>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 14 }}>
            <thead><tr>
              <th style={th}>Month</th>
              <th style={{ ...th, textAlign: 'right' }}>Indexing</th>
              <th style={{ ...th, textAlign: 'right' }}>Search AI</th>
              <th style={{ ...th, textAlign: 'right' }}>Total</th>
            </tr></thead>
            <tbody>
              {(b.months || []).slice(0, 6).map(mo => (
                <tr key={mo.month}>
                  <td style={td}>{mo.month}</td>
                  <td style={num}>{fmtMoney(mo.ingest_cost)}</td>
                  <td style={num}>{fmtMoney(mo.search_cost)}</td>
                  <td style={{ ...num, fontWeight: 700 }}>{fmtMoney(mo.total_cost)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {/* sync runs */}
      {(b?.runs || []).length > 0 && (
        <>
          <div style={{ fontSize: 13, fontWeight: 700, margin: '14px 0 6px' }}>
            🔄 Product syncs</div>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 14 }}>
            <thead><tr>
              <th style={th}>Finished</th>
              <th style={{ ...th, textAlign: 'right' }}>Products</th>
              <th style={{ ...th, textAlign: 'right' }}>AI tokens</th>
              <th style={{ ...th, textAlign: 'right' }}>Cost</th>
            </tr></thead>
            <tbody>
              {(b.runs || []).slice(0, 5).map((r, i) => (
                <tr key={i}>
                  <td style={td}>{(r.finished_at || '').replace('T', ' ').slice(0, 16)}</td>
                  <td style={num}>{r.indexed}</td>
                  <td style={num}>{(r.tokens || 0).toLocaleString()}</td>
                  <td style={num}>{fmtMoney(r.cost)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <div style={{ fontSize: 10, color: '#6b6a8a', borderTop: '1px solid #e2dff0',
                    paddingTop: 8 }}>
        Venue Marketplace · venuemarketplace.xyz · every number in this report comes from your
        own live data — nothing estimated.
      </div>
    </div>,
    document.body
  )
}
