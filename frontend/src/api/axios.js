import axios from 'axios'
import { Message } from 'element-ui'
import { clearUserSessionStorage } from '../utils/session-storage'

const service = axios.create({
  baseURL: '/api',
  timeout: 7500000,
})

// Request interceptor - attach JWT token
service.interceptors.request.use(
  config => {
    const token = sessionStorage.getItem('access_token')
    const body = config.data ? (typeof config.data === 'string' ? config.data : JSON.stringify(config.data)) : ''
    console.log('[axios-req]', config.method?.toUpperCase(), config.url, 'token:', !!token, 'body:', body.substring(0, 200))
    const isAuthRequest = config.url && (config.url.includes('/auth/login') || config.url.includes('/auth/register'))
    if (token && !isAuthRequest) {
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
          if (config.url.includes('/auth/login') || config.url.includes('/auth/register')) {
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
          // JWT token 无效时 flask_jwt_extended 返回 422
          // 静默处理，让页面使用演示数据
          if (config.url && config.url.includes('/domain/')) {
            break
          }
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
