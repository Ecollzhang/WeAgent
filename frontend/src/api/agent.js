import service from './axios'

export function getAgents(classId) {
  const params = classId ? { class_id: classId } : {}
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

export function getCategories() {
  return service.get('/agents/categories')
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
