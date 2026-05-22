import service from './axios'

export function sendMessage(data) {
  return service.post('/messages', data)
}

export function getMessages(conversationId, params) {
  return service.get(`/messages/conversation/${conversationId}`, { params })
}

export function togglePin(messageId) {
  return service.post(`/messages/${messageId}/pin`)
}

export function getPinnedMessages(conversationId) {
  return service.get(`/messages/conversation/${conversationId}/pinned`)
}

export function pollMessages(conversationId, after) {
  const params = after ? { after } : {}
  return service.get(`/messages/poll/${conversationId}`, { params })
}
