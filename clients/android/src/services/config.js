const SERVER_URL_KEY = 'weagent.android.serverUrl'

export function normalizeServerUrl(value) {
  return String(value || '').trim().replace(/\/+$/, '')
}

export async function getServerUrl() {
  return getCurrentServerUrl()
}

export function getCurrentServerUrl() {
  return normalizeServerUrl(localStorage.getItem(SERVER_URL_KEY) || import.meta.env.VITE_DEFAULT_SERVER_URL || '')
}

export async function setServerUrl(value) {
  const serverUrl = normalizeServerUrl(value)
  localStorage.setItem(SERVER_URL_KEY, serverUrl)
  return serverUrl
}

export function apiUrl(serverUrl, path = '') {
  return `${normalizeServerUrl(serverUrl)}/api${path}`
}

export function backendUrl(serverUrl, path = '') {
  const cleanPath = String(path || '')
  if (/^(data:|blob:|https?:\/\/)/i.test(cleanPath)) return cleanPath
  return `${normalizeServerUrl(serverUrl)}${cleanPath.startsWith('/') ? cleanPath : `/${cleanPath}`}`
}
