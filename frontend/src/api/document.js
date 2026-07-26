/**
 * 知识库文档管理 API
 */

import request from './request'

export function listDocuments() {
  return request.get('/documents')
}

export function uploadDocument(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function deleteDocument(id) {
  return request.delete(`/documents/${id}`)
}

export function getDocumentChunks(id, limit = 20) {
  return request.get(`/documents/${id}/chunks`, { params: { limit } })
}

export function getStatsOverview() {
  return request.get('/stats/overview')
}
