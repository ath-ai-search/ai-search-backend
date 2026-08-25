// =====================================================================
// api.js — talks to OUR Ingestion API (FastAPI on port 8100)
// =====================================================================
// Local dev (npm run dev) -> talk to localhost:8100 directly.
// Production build (served BY nginx on the same server as the API)
// -> '' = same origin, nginx forwards /stats etc. to the API.
// Exported: every page must use THIS base — never hardcode localhost.
export const API = import.meta.env.DEV ? 'http://localhost:8100' : ''

// ---------------------------------------------------------------------
// 👥 THE SELECTED CLIENT (multi-tenant switcher)
// App.jsx sets this when you pick a client on top; every data call below
// silently carries it, so ALL pages show that client's world only.
// ---------------------------------------------------------------------
let CLIENT = 'default'
export function setApiClient(id) { CLIENT = id || 'default' }
export function apiClient() { return CLIENT }

function withClient(path) {
  // ALWAYS explicit — even for "default". (Leaving it implicit made the
  // backend fall back to live/platform data and mix clients on screen.)
  return path + (path.includes('?') ? '&' : '?') + 'client_id=' + encodeURIComponent(CLIENT)
}

async function j(path) {
  const r = await fetch(`${API}${path}`)
  return r.json()
}

async function jm(method, path, body) {
  const r = await fetch(`${API}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(data.detail || `${r.status}`)
  return data
}

// ---- per-client data (follow the switcher) ----
export async function getStats()          { return j(withClient('/stats')) }
export async function getSearchAnalytics(size = 30, source = 'all') { return j(withClient(`/stats/search-analytics?size=${size}&source=${source}`)) }
export async function getBilling()        { return j(withClient('/billing/summary')) }
export async function getBillingMonth(m)  { return j(withClient(`/billing/month?month=${m}`)) }
export async function getFields()         { return j(withClient('/fields')) }

// page through EVERY indexed product (the Products page "Show more" button)
export async function getProducts(offset = 0, limit = 30) {
  return j(withClient(`/products?offset=${offset}&limit=${limit}`))
}

export async function search(q, k = 8) {
  return j(withClient(`/search?q=${encodeURIComponent(q)}&k=${k}`))
}

export async function getOpenSearchInfo() { return j(withClient('/opensearch-info')) }

// ---- global data (same for every client — one shared machine) ----
export async function getApiInfo()        { return j('/api-info') }
export async function getShopApiInfo()    { return j('/shop-api-info') }
export async function getAzureInfo()      { return j('/azure/info') }

export async function getHealth() {
  try { return await j('/health') } catch { return { status: 'down', opensearch: false } }
}

// ---------------------------------------------------------------------
// 👥 ADMIN — client management (nginx protects /admin/* with the
// dashboard login, so being logged in here is the authorisation)
// ---------------------------------------------------------------------
export async function getClients()        { return j('/admin/clients') }
export async function getAdminOverview()  { return j('/admin/overview') }
export async function createClient(body)  { return jm('POST', '/admin/clients', body) }
export async function updateClient(id, body) { return jm('PATCH', `/admin/clients/${id}`, body) }
export async function rotateClientKey(id) { return jm('POST', `/admin/clients/${id}/rotate-key`) }
export async function setPortalPassword(id, password) {
  return jm('POST', `/admin/clients/${id}/portal-password`, { password })
}
export async function getAdminTickets(status = '', client_id = '') {
  const q = new URLSearchParams()
  if (status) q.set('status', status)
  if (client_id) q.set('client_id', client_id)
  return j('/admin/tickets' + (q.toString() ? `?${q}` : ''))
}
export async function adminTicketReply(id, body) {
  return jm('POST', `/admin/tickets/${id}/reply`, body)
}
export async function deleteClient(id, deleteData = true, confirm = '') {
  return jm('DELETE', `/admin/clients/${id}?delete_data=${deleteData}&confirm=${encodeURIComponent(confirm)}`)
}
