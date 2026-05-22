import service from './axios'

export function getTools() {
  return service.get('/tools')
}

export function getTool(id) {
  return service.get(`/tools/${id}`)
}

export function createTool(data) {
  return service.post('/tools', data)
}

export function updateTool(id, data) {
  return service.put(`/tools/${id}`, data)
}

export function deleteTool(id) {
  return service.delete(`/tools/${id}`)
}
