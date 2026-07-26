/**
 * 聊天 / WebSocket API
 * ====================
 */

/**
 * 创建 WebSocket 连接用于流式问答。
 *
 * @param {number} conversationId - 会话ID
 * @param {string} question - 用户问题
 * @param {Function} onToken - 收到每个token时的回调
 * @param {Function} onSources - 收到引用来源时的回调
 * @param {Function} onDone - 回答完成时的回调
 * @param {Function} onError - 出错时的回调
 * @returns {WebSocket} WebSocket 实例
 */
export function streamChat(conversationId, question, { onToken, onSources, onDone, onError }) {
  const token = localStorage.getItem('token')
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const wsUrl = `${protocol}//${host}/ws/chat/${conversationId}?token=${token}`

  const ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    // 连接成功，发送问题
    ws.send(JSON.stringify({ question }))
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      switch (data.type) {
        case 'sources':
          onSources && onSources(data.data)
          break
        case 'token':
          onToken && onToken(data.data)
          break
        case 'done':
          onDone && onDone(data.data)
          break
        case 'error':
          onError && onError(data.data)
          break
      }
    } catch (e) {
      console.error('解析 WebSocket 消息失败:', e)
    }
  }

  ws.onerror = (error) => {
    console.error('WebSocket 连接错误:', error)
    onError && onError('连接失败，请检查后端服务是否启动')
  }

  ws.onclose = (event) => {
    if (event.code === 4001) {
      onError && onError('登录已过期，请重新登录')
    } else if (event.code === 4003) {
      onError && onError('无权访问此会话')
    } else if (event.code === 4004) {
      onError && onError('会话不存在')
    }
  }

  return ws
}
