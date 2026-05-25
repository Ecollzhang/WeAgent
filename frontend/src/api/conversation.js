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

export function stopConversationAgent(conversationId, agentId) {
  return service.post(`/conversations/${conversationId}/agents/${agentId}/stop`)
}

export function getConversationAttachments(conversationId) {
  return service.get(`/conversations/${conversationId}/attachments`)
}

export function uploadConversationAttachment(conversationId, file, agentId) {
  const formData = new FormData()
  formData.append('file', file)
  if (agentId) formData.append('agent_id', agentId)
  return service.post(`/conversations/${conversationId}/attachments`, formData)
}

export function deleteConversationAttachment(conversationId, path, agentId) {
  return service.delete(`/conversations/${conversationId}/attachments`, {
    data: { path, agent_id: agentId },
  })
}
