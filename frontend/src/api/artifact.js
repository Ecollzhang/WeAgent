import service from './axios'

export function createArtifact(data) {
  return service.post('/artifacts', data)
}

export function getArtifact(id) {
  return service.get(`/artifacts/${id}`)
}

export function getArtifactsByMessage(messageId) {
  return service.get(`/artifacts/message/${messageId}`)
}

export function updateArtifact(id, data) {
  return service.put(`/artifacts/${id}`, data)
}
