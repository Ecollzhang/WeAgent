import axios from './axios'

// ── 文档管理 ──

export function uploadDocument(formData) {
  return axios.post('/rag/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function fetchFromUrl(data) {
  return axios.post('/rag/documents/fetch-url', data)
}

export function scrapeFromUrl(data) {
  return axios.post('/rag/documents/scrape-url', data)
}

export function previewDocument(docId) {
  return axios.get(`/rag/documents/${docId}/preview`)
}

export function confirmDocument(docId) {
  return axios.post(`/rag/documents/${docId}/confirm`)
}

export function deleteDocument(docId) {
  return axios.delete(`/rag/documents/${docId}`)
}

export function reprocessDocument(docId) {
  return axios.post(`/rag/documents/${docId}/reprocess`)
}

export function listDocuments(params) {
  return axios.get('/rag/documents', { params })
}

export function getDocument(docId) {
  return axios.get(`/rag/documents/${docId}`)
}

// ── 检索 ──

export function semanticSearch(data) {
  return axios.post('/rag/search', data)
}

export function hybridSearch(data) {
  return axios.post('/rag/search/hybrid', data)
}

// ── 状态 ──

export function getRagStatus() {
  return axios.get('/rag/status')
}
