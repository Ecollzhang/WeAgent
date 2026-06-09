import service from './axios'

export function getToolsetCategories() {
  return service.get('/toolsets/categories')
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
