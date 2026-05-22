import axios from 'axios'
import { Message } from 'element-ui'

const service = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// Request interceptor - attach JWT token
service.interceptors.request.use(
  config => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// Response interceptor - handle errors
service.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    const { response } = error

    if (response) {
      const { status, data } = response

      switch (status) {
        case 401:
          // Token expired or invalid
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('user')
          window.location.href = '/login'
          Message.error('Login expired, please login again')
          break
        case 403:
          Message.error('No permission')
          break
        case 404:
          Message.error(data?.message || 'Resource not found')
          break
        case 422:
          Message.error(data?.message || 'Validation error')
          break
        case 500:
          Message.error('Server error')
          break
        default:
          Message.error(data?.message || 'Request failed')
      }
    } else {
      Message.error('Network error, please check your connection')
    }

    return Promise.reject(error)
  }
)

export default service
