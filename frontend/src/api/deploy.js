import service from './axios'

export function createDeploy(data) {
  return service.post('/deploys', data)
}

export function getDeploy(id) {
  return service.get(`/deploys/${id}`)
}

export function getConversationDeploys(conversationId) {
  return service.get(`/deploys/conversation/${conversationId}`)
}
