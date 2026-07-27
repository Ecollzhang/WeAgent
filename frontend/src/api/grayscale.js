import axios from './axios'

// ── Grayscale config ──────────────────────────────────────────────

export function getGrayscaleConfig(domain) {
  return axios.get('/grayscale/config', { params: { domain } })
}

export function getGrayscaleDomains() {
  return axios.get('/grayscale/domains')
}

// ── Admin ─────────────────────────────────────────────────────────

export function updateGrayscaleConfig(id, data) {
  return axios.put(`/admin/grayscale/${id}`, data)
}

export function batchUpdateGrayscaleConfig(updates) {
  return axios.post('/admin/grayscale/batch', { updates })
}

export function createGrayscaleConfig(data) {
  return axios.post('/admin/grayscale', data)
}

export function deleteGrayscaleConfig(id) {
  return axios.delete(`/admin/grayscale/${id}`)
}
