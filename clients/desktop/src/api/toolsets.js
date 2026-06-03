import { request } from '../services/api'

export function getToolsetCategories() {
  return request({ method: 'get', url: '/toolsets/categories' })
}

export function createToolsetCategory(data) {
  return request({ method: 'post', url: '/toolsets/categories', data })
}

export function updateToolsetCategory(id, data) {
  return request({ method: 'put', url: `/toolsets/categories/${id}`, data })
}

export function deleteToolsetCategory(id) {
  return request({ method: 'delete', url: `/toolsets/categories/${id}` })
}
