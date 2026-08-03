import service from './axios'

export function register(data) {
  return service.post('/auth/register', data)
}

export function login(data) {
  return service.post('/auth/login', data)
}

export function getProfile() {
  return service.get('/auth/profile')
}

export function getUsers() {
  return service.get('/auth/users')
}

export function refreshToken() {
  return service.post('/auth/refresh')
}
