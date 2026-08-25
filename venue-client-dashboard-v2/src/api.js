// =====================================================================
// 🔌 CLIENT-API LAYER — every call the portal makes goes through here.
// The session token rides in the Authorization header; a 401 anywhere
// logs the user out cleanly (expired session, paused account…).
// =====================================================================
const BASE = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '')

let onLogout = () => {}
export function setLogoutHandler(fn) { onLogout = fn }

export function getToken() { return localStorage.getItem('portal_token') || '' }
export function setSession(token, client) {
  localStorage.setItem('portal_token', token)
  localStorage.setItem('portal_client', JSON.stringify(client || {}))
}
export function getClient() {
  try { return JSON.parse(localStorage.getItem('portal_client') || '{}') }
  catch { return {} }
}
export function clearSession() {
  localStorage.removeItem('portal_token')
  localStorage.removeItem('portal_client')
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

// ---- auth ----
export const login = (client_id, password) =>
  call('POST', '/client-api/login', { client_id, password })
export const changePassword = (old_password, new_password) =>
  call('POST', '/client-api/change-password', { old_password, new_password })

// ---- data ----
export const getMe        = () => call('GET', '/client-api/me')
export const getOverview  = () => call('GET', '/client-api/overview')
export const getAnalytics = (source = 'all', size = 30, days = 0) =>
  call('GET', `/client-api/analytics?source=${source}&size=${size}${days ? `&days=${days}` : ''}`)
export const getProducts  = (q = '', category = '', page = 1, size = 24) =>
  call('GET', `/client-api/products?q=${encodeURIComponent(q)}&category=${encodeURIComponent(category)}&page=${page}&size=${size}`)
export const getBilling   = () => call('GET', '/client-api/billing')
export const getSync      = () => call('GET', '/client-api/sync')
export const getEvents    = (type = 'all', size = 50) =>
  call('GET', `/client-api/events?type=${encodeURIComponent(type)}&size=${size}`)
export const askAssistant = (question, history = []) =>
  call('POST', '/client-api/assistant', { question, history })

// ---- synonyms (the real ones) ----
export const getSynonyms    = () => call('GET', '/client-api/synonyms')
export const addSynonym     = (a, b) => call('POST', '/client-api/synonyms', { add: [a, b] })
export const removeSynonym  = (a, b) => call('POST', '/client-api/synonyms', { remove: [a, b] })

// ---- support ----
export const getTickets   = () => call('GET', '/client-api/tickets')
export const createTicket = (subject, message, priority = 'normal') =>
  call('POST', '/client-api/tickets', { subject, message, priority })
export const replyTicket  = (ticket_id, message) =>
  call('POST', '/client-api/tickets/reply', { ticket_id, message })
export const resolveTicket = (ticket_id) =>
  call('POST', '/client-api/tickets/reply', { ticket_id, resolve: true })
