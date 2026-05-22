import service from './axios'

export function updateProfile(data) {
  return service.put('/auth/profile', data)
}

export function getModelConfig() {
  return service.get('/settings/model-config')
}

export function saveModelConfig(data) {
  return service.post('/settings/model-config', data)
}
