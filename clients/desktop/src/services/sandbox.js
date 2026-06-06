import axios from 'axios'
import { apiUrl, getServerUrl } from './config'
import { getAccessToken } from './session'

async function createSandboxClient() {
  const serverUrl = await getServerUrl()
  const client = axios.create({
    baseURL: apiUrl(serverUrl),
    timeout: 7500000,
  })

  client.interceptors.request.use(config => {
    const token = getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  client.interceptors.response.use(
    response => response.data,
    error => {
      const { response } = error || {}
      if (response) {
        return Promise.reject(response.data || error)
      }
      return Promise.reject(error)
    }
  )

  return client
}

async function request(config) {
  const client = await createSandboxClient()
  return client.request(config)
}

export function readAgentFile(sessionId, agentId, path) {
  return request({
    method: 'get',
    url: `/sandbox/sessions/${sessionId}/agents/${agentId}/files`,
    params: { path },
  })
}

export async function getAgentFileUrl(sessionId, agentId, path) {
  const serverUrl = await getServerUrl()
  return apiUrl(
    serverUrl,
    `/sandbox/sessions/${encodeURIComponent(sessionId)}/agents/${encodeURIComponent(agentId)}/files/raw?path=${encodeURIComponent(path)}`
  )
}

export async function getWorkspaceFileUrl(sessionId, filepath) {
  const serverUrl = await getServerUrl()
  const clean = String(filepath || '').replace(/^\/?workspace\//, '')
  const encoded = clean.split('/').map(encodeURIComponent).join('/')
  return apiUrl(serverUrl, `/sandbox/sessions/${sessionId}/workspace/${encoded}`)
}

export function getFileTree(sessionId, root = '/workspace') {
  return request({
    method: 'get',
    url: `/sandbox/sessions/${sessionId}/files/tree`,
    params: { root },
  })
}

export function readSessionRawFile(sessionId, path) {
  return request({
    method: 'get',
    url: `/sandbox/sessions/${sessionId}/files/raw`,
    params: { path },
    responseType: 'text',
  })
}

export async function getSessionRawFileUrl(sessionId, path) {
  const serverUrl = await getServerUrl()
  return apiUrl(serverUrl, `/sandbox/sessions/${sessionId}/files/raw?path=${encodeURIComponent(path)}`)
}

export async function getSessionDownloadUrl(sessionId, path) {
  const serverUrl = await getServerUrl()
  return apiUrl(serverUrl, `/sandbox/sessions/${sessionId}/files/download?path=${encodeURIComponent(path)}`)
}

export async function getSessionZipExportUrl(sessionId, path, mode = 'auto', selectedPaths = []) {
  const serverUrl = await getServerUrl()
  const params = new URLSearchParams()
  params.set('path', path)
  params.set('mode', mode)
  ;(selectedPaths || []).forEach(item => {
    if (item) params.append('selected_path', item)
  })
  return apiUrl(serverUrl, `/sandbox/sessions/${sessionId}/files/export-zip?${params.toString()}`)
}

export function writeFile(sessionId, path, content) {
  return request({
    method: 'put',
    url: `/sandbox/sessions/${sessionId}/files/write`,
    data: { path, content },
  })
}

export function listServices(sessionId) {
  return request({
    method: 'get',
    url: `/sandbox/sessions/${sessionId}/services`,
  })
}

export function startService(sessionId, data) {
  return request({
    method: 'post',
    url: `/sandbox/sessions/${sessionId}/services/start`,
    data,
  })
}

export function stopService(sessionId, serviceId) {
  return request({
    method: 'post',
    url: `/sandbox/sessions/${sessionId}/services/${serviceId}/stop`,
  })
}

export function restartService(sessionId, serviceId) {
  return request({
    method: 'post',
    url: `/sandbox/sessions/${sessionId}/services/${serviceId}/restart`,
  })
}

export function refreshServiceToken(sessionId, serviceId, data = {}) {
  return request({
    method: 'post',
    url: `/sandbox/sessions/${sessionId}/services/${serviceId}/token`,
    data,
  })
}

export function getServiceLogs(sessionId, serviceId, tailBytes = 65536) {
  return request({
    method: 'get',
    url: `/sandbox/sessions/${sessionId}/services/${serviceId}/logs`,
    params: { tail_bytes: tailBytes },
  })
}

export function stopAgent(sessionId, agentId) {
  return request({
    method: 'post',
    url: `/sandbox/sessions/${sessionId}/agents/${agentId}/stop`,
  })
}
