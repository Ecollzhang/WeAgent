import axios from 'axios'

// Sandbox API calls can run for a long time while Claude Code is working.
const request = axios.create({
  baseURL: '/api',
  timeout: 7500000, // 125 minutes
})

// Response interceptor - unwrap response.data
request.interceptors.response.use(
  response => response.data,
  error => {
    const { response } = error
    if (response) {
      return Promise.reject(response.data || error)
    }
    return Promise.reject(error)
  }
)

// ===== Image =====
export function getImageStatus() {
  return request.get('/sandbox/image/status')
}

export function buildImage() {
  return request.post('/sandbox/image/build')
}

// ===== Sessions =====
export function createSession(data) {
  return request.post('/sandbox/sessions', data)
}

export function listSessions() {
  return request.get('/sandbox/sessions')
}

export function getSession(sessionId) {
  return request.get(`/sandbox/sessions/${sessionId}`)
}

export function destroySession(sessionId) {
  return request.delete(`/sandbox/sessions/${sessionId}`)
}

export function getStatus() {
  return request.get('/sandbox/status')
}

// ===== Communication =====
export function sendMessage(sessionId, agentId, message) {
  const body = { message }
  if (agentId) body.agent_id = agentId
  return request.post(`/sandbox/sessions/${sessionId}/send`, body)
}

export function sendChain(sessionId, messages) {
  return request.post(`/sandbox/sessions/${sessionId}/chain`, { messages })
}

// ===== Agent =====
export function listAgents(sessionId) {
  return request.get(`/sandbox/sessions/${sessionId}/agents`)
}

export function addSessionAgent(sessionId, data) {
  return request.post(`/sandbox/sessions/${sessionId}/agents`, data)
}

export function removeSessionAgent(sessionId, agentId) {
  return request.delete(`/sandbox/sessions/${sessionId}/agents/${agentId}`)
}

export function getAgentHistory(sessionId, agentId, limit = 0) {
  return request.get(`/sandbox/sessions/${sessionId}/agents/${agentId}/history`, {
    params: { limit },
  })
}

export function getAgentProgress(sessionId, agentId) {
  return request.get(`/sandbox/sessions/${sessionId}/agents/${agentId}/progress`)
}

export function getAgentEvents(sessionId, agentId, since = 0) {
  return request.get(`/sandbox/sessions/${sessionId}/agents/${agentId}/events`, {
    params: { since },
  })
}

// ===== File operations =====
export function readAgentFile(sessionId, agentId, path) {
  return request.get(`/sandbox/sessions/${sessionId}/agents/${agentId}/files`, {
    params: { path },
  })
}

// Build URL for raw file serving (browser-renderable)
export function getAgentFileUrl(sessionId, agentId, path) {
  const base = '/api/sandbox/sessions'
  return `${base}/${sessionId}/agents/${agentId}/files/raw?path=${encodeURIComponent(path)}`
}

// Build workspace URL for proper path resolution (CSS/JS relative to HTML)
export function getWorkspaceFileUrl(sessionId, filepath) {
  // Strip /workspace/ prefix for the URL path
  const clean = filepath.replace(/^\/?workspace\//, '')
  const encoded = clean.split('/').map(encodeURIComponent).join('/')
  return `/api/sandbox/sessions/${sessionId}/workspace/${encoded}`
}

export function getFileTree(sessionId, root = '/workspace') {
  return request.get(`/sandbox/sessions/${sessionId}/files/tree`, {
    params: { root },
  })
}

export function getSessionRawFileUrl(sessionId, path) {
  return `/api/sandbox/sessions/${sessionId}/files/raw?path=${encodeURIComponent(path)}`
}

export function getSessionDownloadUrl(sessionId, path) {
  return `/api/sandbox/sessions/${sessionId}/files/download?path=${encodeURIComponent(path)}`
}

// ===== Custom tools =====
export function listCustomTools(sessionId) {
  return request.get(`/sandbox/sessions/${sessionId}/tools`)
}

export function installCustomTool(sessionId, data) {
  return request.post(`/sandbox/sessions/${sessionId}/tools`, data)
}

export function removeCustomTool(sessionId, toolName) {
  return request.delete(`/sandbox/sessions/${sessionId}/tools/${toolName}`)
}

// ===== Services =====
export function listServices(sessionId) {
  return request.get(`/sandbox/sessions/${sessionId}/services`)
}

export function startService(sessionId, data) {
  return request.post(`/sandbox/sessions/${sessionId}/services/start`, data)
}

export function stopService(sessionId, port) {
  return request.post(`/sandbox/sessions/${sessionId}/services/${port}/stop`)
}

export function getServiceLogs(sessionId, port) {
  return request.get(`/sandbox/sessions/${sessionId}/services/${port}/logs`)
}

// ===== File write-back =====
export function writeFile(sessionId, path, content) {
  return request.put(`/sandbox/sessions/${sessionId}/files/write`, { path, content })
}

// ===== Debug log =====
export function debugLog(label, msg) {
  return request.post('/sandbox/debug/log', { label, msg }).catch(() => {})
}

// ===== Agent control =====
export function stopAgent(sessionId, agentId) {
  return request.post(`/sandbox/sessions/${sessionId}/agents/${agentId}/stop`)
}
