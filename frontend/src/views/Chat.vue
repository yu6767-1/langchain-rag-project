<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { streamChat } from '@/api/chat'
import { ElMessage, ElMessageBox } from 'element-plus'
import { marked } from 'marked'

// 安全配置：禁用原始 HTML，防止 XSS 攻击
marked.setOptions({
  breaks: true,      // 支持换行
  gfm: true,         // GitHub 风格 Markdown（表格、删除线等）
})

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const chat = useChatStore()

const question = ref('')
const loading = ref(false)
const chatContainer = ref(null)
let ws = null

// 初始化：加载会话列表，如果有路由参数则加载对应会话
onMounted(async () => {
  await chat.loadConversations()
  if (route.params.id) {
    chat.switchConversation(Number(route.params.id))
  } else if (chat.conversations.length > 0) {
    chat.switchConversation(chat.conversations[0].id)
    router.replace(`/chat/${chat.conversations[0].id}`)
  }
})

// 滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

// 组件卸载时关闭 WebSocket（防止内存泄漏）
onUnmounted(() => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.close()
    ws = null
  }
})

// 监听消息变化，自动滚动
watch(() => chat.messages.length, scrollToBottom)
watch(() => chat.streamingContent, scrollToBottom)

// 发送消息
async function sendMessage() {
  const q = question.value.trim()
  if (!q || loading.value) return

  // 如果没有当前会话，先创建
  if (!chat.currentConversationId) {
    await chat.createNewConversation()
    router.replace(`/chat/${chat.currentConversationId}`)
  }

  // 添加用户消息到界面
  chat.addUserMessage(q)
  question.value = ''
  chat.startStreaming()
  loading.value = true
  scrollToBottom()

  // 建立 WebSocket 连接进行流式问答
  ws = streamChat(chat.currentConversationId, q, {
    onSources(sources) {
      chat.setSources(sources)
    },
    onToken(token) {
      chat.appendToken(token)
      scrollToBottom()
    },
    onDone(fullContent) {
      chat.finishStreaming(fullContent)
      loading.value = false
      ws = null
      // 刷新会话列表（更新标题等）
      chat.loadConversations()
      scrollToBottom()
    },
    onError(error) {
      ElMessage.error(error)
      loading.value = false
      ws = null
    }
  })
}

// 新建会话
async function newConversation() {
  await chat.createNewConversation()
  router.replace(`/chat/${chat.currentConversationId}`)
}

// 切换会话
function selectConversation(id) {
  chat.switchConversation(id)
  router.replace(`/chat/${id}`)
}

// 删除会话
async function handleDeleteConversation(id) {
  try {
    await ElMessageBox.confirm('确定要删除这个会话吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await chat.removeConversation(id)
    if (chat.currentConversationId === id) {
      chat.currentConversationId = null
      chat.messages = []
      router.replace('/chat')
    }
    ElMessage.success('会话已删除')
  } catch {
    // 用户取消
  }
}

// 安全解析后端返回的时间字符串（后端存 UTC 但序列化时可能丢失时区标记）
function parseDate(dateStr) {
  if (!dateStr) return null
  // 如果字符串没有时区信息（没有 Z 也没有 +HH:MM），手动补充 Z（表示 UTC）
  const safeStr = dateStr.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(dateStr)
    ? dateStr
    : dateStr + 'Z'
  return new Date(safeStr)
}

// 格式化时间（会话列表用 — 显示完整日期时间）
function formatTime(dateStr) {
  if (!dateStr) return ''
  const d = parseDate(dateStr)
  if (!d) return ''
  const now = new Date()
  // 今天的显示"今天 HH:mm"
  if (d.toDateString() === now.toDateString()) {
    return `今天 ${d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`
  }
  // 昨天的显示"昨天 HH:mm"
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)
  if (d.toDateString() === yesterday.toDateString()) {
    return `昨天 ${d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`
  }
  // 更早的显示完整日期时间
  return d.toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

// 格式化消息时间（精确到分钟）
function formatMsgTime(dateStr) {
  if (!dateStr) return ''
  const d = parseDate(dateStr)
  if (!d) return ''
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// 安全的 HTML 转义（只保留安全的 Markdown 渲染结果，去除危险标签）
function escapeHtml(text) {
  return text
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<iframe[\s\S]*?<\/iframe>/gi, '')
    .replace(/<object[\s\S]*?<\/object>/gi, '')
    .replace(/<embed[\s\S]*?>/gi, '')
    .replace(/on\w+\s*=\s*"[^"]*"/gi, '')
    .replace(/on\w+\s*=\s*'[^']*'/gi, '')
}

// Markdown 渲染（已做 XSS 防护）
function renderMarkdown(text) {
  if (!text) return ''
  const html = marked(text)
  return escapeHtml(html)
}
</script>

<template>
  <div class="chat-layout">
    <!-- 左侧会话列表 -->
    <div class="chat-sidebar">
      <div class="sidebar-header">
        <el-button type="primary" @click="newConversation" style="width: 100%">
          <el-icon><Plus /></el-icon> 新建会话
        </el-button>
      </div>
      <div class="conversation-list">
        <div
          v-for="conv in chat.conversations"
          :key="conv.id"
          :class="['conv-item', { active: conv.id === chat.currentConversationId }]"
          @click="selectConversation(conv.id)"
        >
          <div class="conv-info">
            <div class="conv-title">{{ conv.title }}</div>
            <div class="conv-meta">
              <span>{{ conv.message_count }} 条消息</span>
              <span>{{ formatTime(conv.updated_at) }}</span>
            </div>
          </div>
          <el-button
            class="conv-delete"
            text
            size="small"
            @click.stop="handleDeleteConversation(conv.id)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <el-empty v-if="chat.conversations.length === 0" description="暂无会话" :image-size="60" />
      </div>
    </div>

    <!-- 右侧聊天区域 -->
    <div class="chat-main">
      <div class="chat-messages" ref="chatContainer">
        <div v-if="!chat.currentConversationId" class="chat-welcome">
          <h1>💬 王雨的 AI 简历助手</h1>
          <p>点击左侧「新建会话」开始对话，了解王雨的技术能力、项目经历和成长故事</p>
          <p class="welcome-hint">试试问：王雨的技术栈是什么？做过什么项目？对 AI 的看法？</p>
        </div>

        <!-- 消息列表 -->
        <div v-for="(msg, index) in chat.messages" :key="msg.id" class="message-wrapper">
          <!-- 当会话切换或第一条消息时显示时间标记 -->
          <div
            v-if="index === 0 || (msg.created_at && index > 0 && chat.messages[index-1].created_at &&
              parseDate(msg.created_at) && parseDate(chat.messages[index-1].created_at) &&
              parseDate(msg.created_at).getTime() - parseDate(chat.messages[index-1].created_at).getTime() > 1800000)"
            class="time-divider"
          >
            <span>{{ formatTime(msg.created_at) }}</span>
          </div>
          <div :class="['message', msg.role === 'user' ? 'msg-user' : 'msg-assistant']">
            <div class="msg-avatar">
              {{ msg.role === 'user' ? '👤' : '🤖' }}
            </div>
            <div class="msg-body">
              <div class="msg-content" v-html="renderMarkdown(msg.content)"></div>
              <!-- 消息时间 -->
              <div class="msg-time">{{ formatMsgTime(msg.created_at) }}</div>
              <!-- 引用来源 -->
              <div v-if="msg.sources && msg.sources.length > 0" class="msg-sources">
                <div class="sources-title">📎 引用来源：</div>
                <div v-for="(src, idx) in msg.sources" :key="idx" class="source-item">
                  <el-tag size="small" type="info">{{ src.filename }}</el-tag>
                  <span class="source-text">{{ src.content?.substring(0, 100) }}...</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 流式生成中的消息 -->
        <div v-if="chat.isStreaming" class="message-wrapper">
          <div class="message msg-assistant">
            <div class="msg-avatar">🤖</div>
            <div class="msg-body">
              <div class="msg-content" v-html="renderMarkdown(chat.streamingContent)"></div>
              <span class="streaming-indicator">
                <el-icon class="is-loading"><Loading /></el-icon> 生成中...
              </span>
              <!-- 流式生成中的引用来源 -->
              <div v-if="chat.streamingSources.length > 0" class="msg-sources">
                <div class="sources-title">📎 引用来源：</div>
                <div v-for="(src, idx) in chat.streamingSources" :key="idx" class="source-item">
                  <el-tag size="small" type="info">{{ src.filename }}</el-tag>
                  <span class="source-text">{{ src.content?.substring(0, 100) }}...</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="chat-input">
        <el-input
          v-model="question"
          type="textarea"
          :rows="2"
          placeholder="问我任何关于王雨的问题，例如：王雨的技术能力如何？做过什么项目？"
          :disabled="loading"
          @keyup.enter.exact="sendMessage"
          resize="none"
        />
        <el-button
          type="primary"
          :loading="loading"
          :disabled="!question.trim()"
          @click="sendMessage"
          class="send-btn"
        >
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-layout {
  display: flex;
  height: 100%;
}

/* ===== 左侧栏 ===== */
.chat-sidebar {
  width: 280px;
  background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.conv-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background 0.15s;
}

.conv-item:hover {
  background: #f5f7fa;
}

.conv-item.active {
  background: #ecf5ff;
  border: 1px solid #d9ecff;
}

.conv-info {
  flex: 1;
  min-width: 0;
}

.conv-title {
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conv-meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.conv-delete {
  opacity: 0;
  transition: opacity 0.15s;
}

.conv-item:hover .conv-delete {
  opacity: 1;
}

/* ===== 聊天区域 ===== */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #f5f7fa;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.chat-welcome {
  text-align: center;
  padding-top: 120px;
  color: #606266;
}

.chat-welcome h1 {
  font-size: 28px;
  margin-bottom: 12px;
}

.chat-welcome p {
  font-size: 15px;
  color: #909399;
}

.welcome-hint {
  margin-top: 24px;
  font-size: 13px;
  color: #c0c4cc;
}

/* ===== 消息 ===== */
.message-wrapper {
  margin-bottom: 20px;
}

.message {
  display: flex;
  gap: 12px;
}

/* 用户消息靠右 */
.msg-user {
  flex-direction: row-reverse;
}

/* AI 消息靠左（默认） */
.msg-assistant {
  flex-direction: row;
}

.msg-avatar {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
  border-radius: 8px;
  background: #fff;
}

.msg-body {
  max-width: 75%;
}

/* 用户消息内容右对齐 */
.msg-user .msg-body {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.msg-content {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}

.msg-content :deep(p) { margin: 0 0 8px; }
.msg-content :deep(ul), .msg-content :deep(ol) { padding-left: 20px; margin: 8px 0; }
.msg-content :deep(code) { background: rgba(0,0,0,0.06); padding: 2px 6px; border-radius: 3px; font-size: 13px; }
.msg-content :deep(pre) { background: #282c34; color: #abb2bf; padding: 12px; border-radius: 6px; overflow-x: auto; }
.msg-content :deep(table) { border-collapse: collapse; width: 100%; margin: 8px 0; }
.msg-content :deep(th), .msg-content :deep(td) { border: 1px solid #dcdfe6; padding: 6px 12px; text-align: left; }
.msg-content :deep(th) { background: #f5f7fa; }

.msg-user .msg-content {
  background: #409eff;
  color: #fff;
}

.msg-assistant .msg-content {
  background: #fff;
  border: 1px solid #e4e7ed;
}

/* 消息时间戳 */
.msg-time {
  font-size: 11px;
  color: #909399;
  margin-top: 4px;
}

/* 时间分隔线（会话开始 / 间隔超过30分钟时显示） */
.time-divider {
  text-align: center;
  margin: 16px 0;
}

.time-divider span {
  display: inline-block;
  padding: 4px 12px;
  background: #e4e7ed;
  border-radius: 12px;
  font-size: 12px;
  color: #909399;
}

/* 引用来源 */
.msg-sources {
  margin-top: 8px;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.sources-title {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.source-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 4px;
}

.source-text {
  font-size: 12px;
  color: #606266;
  line-height: 1.5;
}

.streaming-indicator {
  font-size: 12px;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
}

/* ===== 输入区域 ===== */
.chat-input {
  padding: 16px 24px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.chat-input :deep(.el-textarea__inner) {
  border-radius: 10px;
}

.send-btn {
  height: 40px;
  border-radius: 10px;
  padding: 0 24px;
}
</style>
