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

export function importMcpManifest(data) {
  return service.post('/capabilities/import/mcp-manifest', data)
}

export function previewCapabilityImport(data) {
  return service.post('/capabilities/import/preview', data)
}

export function confirmCapabilityImport(data) {
  return service.post('/capabilities/import/confirm', data)
}

export function getCapabilityAssets(id, params = {}) {
  return service.get(`/capabilities/${id}/assets`, { params })
}

export function getCapabilityAudits(id) {
  return service.get(`/capabilities/${id}/audits`)
}

export function getCapabilityDeleteImpact(id) {
  return service.get(`/capabilities/${id}/delete-impact`)
}

export function deleteCapability(id) {
  return service.delete(`/capabilities/${id}`)
}

export function getProviderConfigs(id) {
  return service.get(`/capabilities/${id}/provider-configs`)
}

export function createProviderConfig(id, data) {
  return service.post(`/capabilities/${id}/provider-configs`, data)
}

export function updateProviderConfig(id, configId, data) {
  return service.put(`/capabilities/${id}/provider-configs/${configId}`, data)
}

export function testProviderConfig(id, configId) {
  return service.post(`/capabilities/${id}/provider-configs/${configId}/test`)
}

export function enableProviderConfig(id, configId) {
  return service.post(`/capabilities/${id}/provider-configs/${configId}/enable`)
}

export function disableProviderConfig(id, configId) {
  return service.post(`/capabilities/${id}/provider-configs/${configId}/disable`)
}

export function deleteProviderConfig(id, configId) {
  return service.delete(`/capabilities/${id}/provider-configs/${configId}`)
}

export function bindAgentCapability(agentId, data) {
  return service.post(`/agents/${agentId}/capabilities`, data)
}

export function updateAgentCapability(agentId, bindingId, data) {
  return service.put(`/agents/${agentId}/capabilities/${bindingId}`, data)
}

export function deleteAgentCapability(agentId, bindingId) {
  return service.delete(`/agents/${agentId}/capabilities/${bindingId}`)
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
