import service from './axios'

export function uploadFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  return service.post('/upload', formData)
}
