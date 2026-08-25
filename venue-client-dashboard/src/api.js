// =====================================================================
// 🔌 VENUE PORTAL API LAYER — session token + every call in one place
// =====================================================================
const BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '')

let onLogout = () => {}
export function setLogoutHandler(fn) { onLogout = fn }
export function getToken() { return localStorage.getItem('venue_token') || '' }
export function setSession(token, client) {
  localStorage.setItem('venue_token', token)
  localStorage.setItem('venue_client', JSON.stringify(client || {}))
}
export function getClient() {
  try { return JSON.parse(localStorage.getItem('venue_client') || '{}') }
  catch { return {} }
}
export function clearSession() {
  localStorage.removeItem('venue_token')
  localStorage.removeItem('venue_client')
}

async function call(method, path, body) {
  const r = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (r.status === 401 && !path.endsWith('/login')) {
    clearSession(); onLogout()
    throw new Error('Session ended — please sign in again')
  }
  const data = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(data.detail || `Error ${r.status}`)
  return data
}

export const login = (client_id, password) =>
  call('POST', '/portal-api/login', { client_id, password })
export const getMe       = () => call('GET', '/portal-api/me')
export const getOverview = () => call('GET', '/portal-api/overview')
export const getEvents   = (type = 'all', size = 60) =>
  call('GET', `/portal-api/events?type=${encodeURIComponent(type)}&size=${size}`)
export const getTrending = () => call('GET', '/portal-api/trending')
export const getProducts = (qq = '', page = 1, size = 24) =>
  call('GET', `/portal-api/products?qq=${encodeURIComponent(qq)}&page=${page}&size=${size}`)
export const askAssistant = (question) =>
  call('POST', '/portal-api/assistant', { question })

// 👑 admin-only
export const getSystem = () => call('GET', '/portal-api/admin/system')
