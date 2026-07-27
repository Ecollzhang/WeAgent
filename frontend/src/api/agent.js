import service from './axios'

export function getAgents(classId, domain) {
  const params = {}
  if (classId) params.class_id = classId
  if (domain) params.domain = domain
  return service.get('/agents', { params })
}

export function getAgent(id) {
  return service.get(`/agents/${id}`)
}

export function createAgent(data) {
  return service.post('/agents', data)
}

export function updateAgent(id, data) {
  return service.put(`/agents/${id}`, data)
}

export function deleteAgent(id) {
  return service.delete(`/agents/${id}`)
}

// ── Categories ──

export function getCategories(domain) {
  const params = {}
  if (domain) params.domain = domain
  return service.get('/agents/categories', { params })
}

export function createCategory(data) {
  return service.post('/agents/categories', data)
}

export function updateCategory(id, data) {
  return service.put(`/agents/categories/${id}`, data)
}

export function deleteCategory(id) {
  return service.delete(`/agents/categories/${id}`)
}
