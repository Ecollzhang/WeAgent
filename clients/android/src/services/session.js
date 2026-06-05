import { getServerUrl } from './config'

const ACCESS_TOKEN_KEY = 'weagent.android.accessToken'
const REFRESH_TOKEN_KEY = 'weagent.android.refreshToken'
const USER_KEY = 'weagent.android.user'

export async function hasServerUrl() {
  return Boolean(await getServerUrl())
}

export function hasAccessToken() {
  return Boolean(localStorage.getItem(ACCESS_TOKEN_KEY))
}

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY) || ''
}

export function getCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  } catch (error) {
    return null
  }
}

export function saveCurrentUser(user) {
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function saveAuth(data) {
  const user = data?.user || null
  const accessToken = data?.access_token || ''
  const refreshToken = data?.refresh_token || ''
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
  if (accessToken) localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  if (refreshToken) localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
}

export function clearAuth() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}
