import { request } from '../services/api'

export function getCapabilities(params = {}) {
  return request({ method: 'get', url: '/capabilities', params })
}

export function getCapability(id) {
  return request({ method: 'get', url: `/capabilities/${id}` })
}

export function getCapabilityVersions(id) {
  return request({ method: 'get', url: `/capabilities/${id}/versions` })
}

export function createSkill(data) {
  return request({ method: 'post', url: '/capabilities/skills', data })
}

export function createCapabilityVersion(id, data) {
  return request({ method: 'post', url: `/capabilities/${id}/versions`, data })
}

export function importSkillMarkdown(data) {
  return request({ method: 'post', url: '/capabilities/import/markdown', data })
}

export function importNpxManifest(data) {
  return request({ method: 'post', url: '/capabilities/import/npx-manifest', data })
}

export function importMcpManifest(data) {
  return request({ method: 'post', url: '/capabilities/import/mcp-manifest', data })
}

export function previewCapabilityImport(data) {
  return request({ method: 'post', url: '/capabilities/import/preview', data })
}

export function confirmCapabilityImport(data) {
  return request({ method: 'post', url: '/capabilities/import/confirm', data })
}

export function getCapabilityAssets(id, params = {}) {
  return request({ method: 'get', url: `/capabilities/${id}/assets`, params })
}

export function getCapabilityAudits(id) {
  return request({ method: 'get', url: `/capabilities/${id}/audits` })
}

export function getCapabilityDeleteImpact(id) {
  return request({ method: 'get', url: `/capabilities/${id}/delete-impact` })
}

export function deleteCapability(id) {
  return request({ method: 'delete', url: `/capabilities/${id}` })
}

export function getProviderConfigs(id) {
  return request({ method: 'get', url: `/capabilities/${id}/provider-configs` })
}

export function createProviderConfig(id, data) {
  return request({ method: 'post', url: `/capabilities/${id}/provider-configs`, data })
}

export function updateProviderConfig(id, configId, data) {
  return request({ method: 'put', url: `/capabilities/${id}/provider-configs/${configId}`, data })
}

export function testProviderConfig(id, configId) {
  return request({ method: 'post', url: `/capabilities/${id}/provider-configs/${configId}/test` })
}

export function enableProviderConfig(id, configId) {
  return request({ method: 'post', url: `/capabilities/${id}/provider-configs/${configId}/enable` })
}

export function disableProviderConfig(id, configId) {
  return request({ method: 'post', url: `/capabilities/${id}/provider-configs/${configId}/disable` })
}

export function deleteProviderConfig(id, configId) {
  return request({ method: 'delete', url: `/capabilities/${id}/provider-configs/${configId}` })
}

export function bindAgentCapability(agentId, data) {
  return request({ method: 'post', url: `/agents/${agentId}/capabilities`, data })
}

export function updateAgentCapability(agentId, bindingId, data) {
  return request({ method: 'put', url: `/agents/${agentId}/capabilities/${bindingId}`, data })
}

export function deleteAgentCapability(agentId, bindingId) {
  return request({ method: 'delete', url: `/agents/${agentId}/capabilities/${bindingId}` })
}

export function getAgentCapabilities(agentId) {
  return request({ method: 'get', url: `/agents/${agentId}/capabilities` })
}

export function getAgentCapabilityUpgrades(agentId) {
  return request({ method: 'get', url: `/agents/${agentId}/capabilities/upgrades` })
}

export function getCapabilityDrafts(params = {}) {
  return request({ method: 'get', url: '/capabilities/drafts', params })
}

export function publishCapabilityDraft(draftId, data = {}) {
  return request({ method: 'post', url: `/capabilities/drafts/${draftId}/publish`, data })
}

export function forkCapabilityDraft(draftId, data = {}) {
  return request({ method: 'post', url: `/capabilities/drafts/${draftId}/fork`, data })
}

export function syncCapabilityCalls(data) {
  return request({ method: 'post', url: '/capabilities/calls/sync', data })
}

export function getCapabilityCalls(params = {}) {
  return request({ method: 'get', url: '/capabilities/calls', params })
}
