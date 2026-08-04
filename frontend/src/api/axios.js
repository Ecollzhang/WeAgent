import axios from 'axios'
import { Message } from 'element-ui'

const service = axios.create({
  baseURL: '/api',
  timeout: 7500000,
})

// Request interceptor - attach JWT token
service.interceptors.request.use(
  config => {
    const token = sessionStorage.getItem('access_token')
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
    if (response.config && response.config.returnFullResponse) {
      return response
    }
    return response.data
  },
  error => {
    const { response, config = {} } = error

    if (response) {
      const { status, data } = response

      switch (status) {
        case 401:
          if (config.url === '/auth/login' || config.url === '/auth/register') {
            Message.error(data?.message || '用户名或密码错误')
          } else {
            // Token expired or invalid
            sessionStorage.removeItem('access_token')
            sessionStorage.removeItem('refresh_token')
            sessionStorage.removeItem('user')
            window.location.href = '/login'
            Message.error('Login expired, please login again')
          }
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
          Message.error(data?.message || '服务端处理失败，请稍后重试')
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
