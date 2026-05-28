import service from './axios'

export function getCapabilities(params = {}) {
  return service.get('/capabilities', { params })
}

export function getCapability(id) {
  return service.get(`/capabilities/${id}`)
}

export function getCapabilityVersions(id) {
  return service.get(`/capabilities/${id}/versions`)
}

export function createSkill(data) {
  return service.post('/capabilities/skills', data)
}

export function createCapabilityVersion(id, data) {
  return service.post(`/capabilities/${id}/versions`, data)
}

export function importSkillMarkdown(data) {
  return service.post('/capabilities/import/markdown', data)
}

export function importNpxManifest(data) {
  return service.post('/capabilities/import/npx-manifest', data)
}

export function bindAgentCapability(agentId, data) {
  return service.post(`/agents/${agentId}/capabilities`, data)
}

export function updateAgentCapability(agentId, bindingId, data) {
  return service.put(`/agents/${agentId}/capabilities/${bindingId}`, data)
}

export function getAgentCapabilities(agentId) {
  return service.get(`/agents/${agentId}/capabilities`)
}

export function getAgentCapabilityUpgrades(agentId) {
  return service.get(`/agents/${agentId}/capabilities/upgrades`)
}

export function getCapabilityDrafts(params = {}) {
  return service.get('/capabilities/drafts', { params })
}

export function publishCapabilityDraft(draftId, data = {}) {
  return service.post(`/capabilities/drafts/${draftId}/publish`, data)
}

export function forkCapabilityDraft(draftId, data = {}) {
  return service.post(`/capabilities/drafts/${draftId}/fork`, data)
}

export function syncCapabilityCalls(data) {
  return service.post('/capabilities/calls/sync', data)
}

export function getCapabilityCalls(params = {}) {
  return service.get('/capabilities/calls', { params })
}
