import axios from 'axios'
import { getServerUrl, apiUrl } from './config'
import { getAccessToken, saveAuth } from './session'

async function request(config) {
  const serverUrl = await getServerUrl()
  const client = axios.create({
    baseURL: apiUrl(serverUrl),
    timeout: 7500000,
  })

  client.interceptors.request.use(req => {
    const token = getAccessToken()
    if (token) req.headers.Authorization = `Bearer ${token}`
    return req
  })

  const response = await client.request(config)
  return response.data
}

export async function testServer(serverUrl) {
  const response = await axios.get(apiUrl(serverUrl, '/health'), { timeout: 8000 })
  return response.data
}

export async function login(credentials) {
  const response = await request({ method: 'post', url: '/auth/login', data: credentials })
  if (response.code === 200) saveAuth(response.data)
  return response
}

export async function register(payload) {
  const response = await request({ method: 'post', url: '/auth/register', data: payload })
  if (response.code === 201) saveAuth(response.data)
  return response
}

export function getConversations() {
  return request({ method: 'get', url: '/conversations' })
}

export function createConversation(data) {
  return request({ method: 'post', url: '/conversations', data })
}

export function deleteConversation(id) {
  return request({ method: 'delete', url: `/conversations/${id}` })
}

export function updateConversationFavorite(id, isFavorite) {
  return request({
    method: 'post',
    url: `/conversations/${id}/favorite`,
    data: { is_favorite: isFavorite },
  })
}

export function getConversationAttachments(conversationId, agentId = '') {
  return request({
    method: 'get',
    url: `/conversations/${conversationId}/attachments`,
    params: agentId ? { agent_id: agentId } : {},
  })
}

export function uploadConversationAttachment(conversationId, file, agentId = '') {
  const formData = new FormData()
  formData.append('file', file)
  if (agentId) formData.append('agent_id', agentId)
  return request({
    method: 'post',
    url: `/conversations/${conversationId}/attachments`,
    data: formData,
  })
}

export function deleteConversationAttachment(conversationId, path, agentId = '') {
  return request({
    method: 'delete',
    url: `/conversations/${conversationId}/attachments`,
    data: { path, agent_id: agentId },
  })
}

export function getMessages(conversationId, params = {}) {
  return request({
    method: 'get',
    url: `/messages/conversation/${conversationId}`,
    params,
  })
}

export function sendMessage(data) {
  return request({ method: 'post', url: '/messages', data })
}

export function getAgents(classId) {
  return request({
    method: 'get',
    url: '/agents',
    params: classId ? { class_id: classId } : {},
  })
}

export function createAgent(data) {
  return request({ method: 'post', url: '/agents', data })
}

export function updateAgent(id, data) {
  return request({ method: 'put', url: `/agents/${id}`, data })
}

export function deleteAgent(id) {
  return request({ method: 'delete', url: `/agents/${id}` })
}

export function getTools() {
  return request({ method: 'get', url: '/tools' })
}

export function getProfile() {
  return request({ method: 'get', url: '/auth/profile' })
}

export function updateProfile(data) {
  return request({ method: 'put', url: '/auth/profile', data })
}

export function getModelConfig() {
  return request({ method: 'get', url: '/settings/model-config' })
}

export function saveModelConfig(data) {
  return request({ method: 'post', url: '/settings/model-config', data })
}

export function uploadFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    method: 'post',
    url: '/upload',
    data: formData,
  })
}

export function getFileTree(sessionId, root = '/workspace') {
  return request({
    method: 'get',
    url: `/sandbox/sessions/${sessionId}/files/tree`,
    params: { root },
  })
}

export function listSandboxServices(sessionId) {
  return request({
    method: 'get',
    url: `/sandbox/sessions/${sessionId}/services`,
  })
}

export function getSandboxServiceLogs(sessionId, serviceId, tailBytes = 65536) {
  return request({
    method: 'get',
    url: `/sandbox/sessions/${sessionId}/services/${serviceId}/logs`,
    params: { tail_bytes: tailBytes },
  })
}

export function restartSandboxService(sessionId, serviceId) {
  return request({
    method: 'post',
    url: `/sandbox/sessions/${sessionId}/services/${serviceId}/restart`,
  })
}

export function stopSandboxService(sessionId, serviceId) {
  return request({
    method: 'post',
    url: `/sandbox/sessions/${sessionId}/services/${serviceId}/stop`,
  })
}

export function readAgentFile(sessionId, agentId, path) {
  return request({
    method: 'get',
    url: `/sandbox/sessions/${sessionId}/agents/${agentId}/files`,
    params: { path },
  })
}

export async function getWorkspaceFileUrl(sessionId, filepath) {
  const serverUrl = await getServerUrl()
  const clean = String(filepath || '').replace(/^\/?workspace\//, '')
  const encoded = clean.split('/').map(encodeURIComponent).join('/')
  return apiUrl(serverUrl, `/sandbox/sessions/${sessionId}/workspace/${encoded}`)
}

export async function getAgentFileUrl(sessionId, agentId, path) {
  const serverUrl = await getServerUrl()
  return apiUrl(
    serverUrl,
    `/sandbox/sessions/${encodeURIComponent(sessionId)}/agents/${encodeURIComponent(agentId)}/files/raw?path=${encodeURIComponent(path)}`
  )
}
