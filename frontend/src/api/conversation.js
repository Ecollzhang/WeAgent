import service from './axios'

export function getConversations() {
  return service.get('/conversations')
}

export function createConversation(data) {
  return service.post('/conversations', data)
}

export function getConversation(id) {
  return service.get(`/conversations/${id}`)
}

export function deleteConversation(id) {
  return service.delete(`/conversations/${id}`)
}

export function addParticipant(conversationId, data) {
  return service.post(`/conversations/${conversationId}/participants`, data)
}

export function removeParticipant(conversationId, participantType, participantId) {
  return service.delete(`/conversations/${conversationId}/participants/${participantType}/${participantId}`)
}
