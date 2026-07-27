import service from './axios'

export function getToolsetCategories(domain) {
  const params = {}
  if (domain) params.domain = domain
  return service.get('/toolsets/categories', { params })
}

export function createToolsetCategory(data) {
  return service.post('/toolsets/categories', data)
}

export function updateToolsetCategory(id, data) {
  return service.put(`/toolsets/categories/${id}`, data)
}

export function deleteToolsetCategory(id) {
  return service.delete(`/toolsets/categories/${id}`)
}
