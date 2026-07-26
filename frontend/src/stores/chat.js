/**
 * 聊天状态管理
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listConversations, createConversation, deleteConversation, getMessages } from '@/api/conversation'

export const useChatStore = defineStore('chat', () => {
  // ===== 状态 =====
  const conversations = ref([])
  const currentConversationId = ref(null)
  const messages = ref([])
  const isStreaming = ref(false)
  const streamingContent = ref('')
  const streamingSources = ref([])

  // ===== 方法 =====

  async function loadConversations() {
    try {
      const res = await listConversations()
      conversations.value = res.conversations
    } catch {
      conversations.value = []
    }
  }

  async function createNewConversation(title = '新建会话') {
    const res = await createConversation(title)
    await loadConversations()
    currentConversationId.value = res.id
    messages.value = []
    return res
  }

  async function removeConversation(id) {
    await deleteConversation(id)
    if (currentConversationId.value === id) {
      currentConversationId.value = null
      messages.value = []
    }
    await loadConversations()
  }

  async function loadMessages(conversationId) {
    try {
      const res = await getMessages(conversationId)
      messages.value = res.messages || []
    } catch {
      messages.value = []
    }
  }

  function switchConversation(conversationId) {
    currentConversationId.value = conversationId
    loadMessages(conversationId)
  }

  function addUserMessage(content) {
    messages.value.push({
      id: Date.now(),
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    })
  }

  function startStreaming() {
    isStreaming.value = true
    streamingContent.value = ''
    streamingSources.value = []
  }

  function appendToken(token) {
    streamingContent.value += token
  }

  function setSources(sources) {
    streamingSources.value = sources
  }

  function finishStreaming(fullContent) {
    isStreaming.value = false
    // 添加助手消息
    messages.value.push({
      id: Date.now() + 1,
      role: 'assistant',
      content: fullContent,
      sources: streamingSources.value,
      created_at: new Date().toISOString(),
    })
    streamingContent.value = ''
    streamingSources.value = []
  }

  return {
    conversations,
    currentConversationId,
    messages,
    isStreaming,
    streamingContent,
    streamingSources,
    loadConversations,
    createNewConversation,
    removeConversation,
    loadMessages,
    switchConversation,
    addUserMessage,
    startStreaming,
    appendToken,
    setSources,
    finishStreaming,
  }
})
