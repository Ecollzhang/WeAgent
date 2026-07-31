import axios from './axios'

// ── 文档管理 ──

export function uploadDocument(formData) {
  return axios.post('/domain/rag/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function fetchFromUrl(data) {
  return axios.post('/domain/rag/documents/fetch-url', data)
}

export function scrapeFromUrl(data) {
  return axios.post('/domain/rag/documents/scrape-url', data)
}

export function previewDocument(docId) {
  return axios.get(`/domain/rag/documents/${docId}/preview`)
}

export function confirmDocument(docId) {
  return axios.post(`/domain/rag/documents/${docId}/confirm`)
}

export function deleteDocument(docId) {
  return axios.delete(`/domain/rag/documents/${docId}`)
}

export function reprocessDocument(docId) {
  return axios.post(`/domain/rag/documents/${docId}/reprocess`)
}

export function listDocuments(params) {
  return axios.get('/domain/rag/documents', { params })
}

export function getDocument(docId) {
  return axios.get(`/domain/rag/documents/${docId}`)
}

// ── 检索 ──

export function semanticSearch(data) {
  return axios.post('/domain/rag/search', data)
}

export function hybridSearch(data) {
  return axios.post('/domain/rag/search/hybrid', data)
}

// ── 状态 ──

export function getRagStatus() {
  return axios.get('/domain/rag/status')
}
