import axios from './axios'

// ── Workspace CRUD ────────────────────────────────────────────────

export function getWorkspaces(domain = '') {
  return axios.get('/workspaces', { params: domain ? { domain } : {} })
}

export function getWorkspace(id) {
  return axios.get(`/workspaces/${id}`)
}

export function createWorkspace(data) {
  return axios.post('/workspaces', data)
}

export function updateWorkspace(id, data) {
  return axios.put(`/workspaces/${id}`, data)
}

export function archiveWorkspace(id) {
  return axios.delete(`/workspaces/${id}`)
}

export function deleteWorkspace(id) {
  return axios.delete(`/workspaces/${id}/permanent`)
}
