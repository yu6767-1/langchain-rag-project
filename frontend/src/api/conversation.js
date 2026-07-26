/**
 * 会话 API
 */

import request from './request'

export function listConversations() {
  return request.get('/conversations')
}

export function createConversation(title = '新建会话') {
  return request.post('/conversations', { title })
}

export function deleteConversation(id) {
  return request.delete(`/conversations/${id}`)
}

export function updateConversationTitle(id, title) {
  return request.put(`/conversations/${id}`, { title })
}

export function getMessages(conversationId, limit = 50, offset = 0) {
  return request.get(`/conversations/${conversationId}/messages`, {
    params: { limit, offset }
  })
}

export function submitFeedback(messageId, feedback) {
  return request.post(`/conversations/messages/${messageId}/feedback`, { feedback })
}
