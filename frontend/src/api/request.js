/**
 * Axios 实例配置
 * ===============
 * 统一管理 HTTP 请求的配置：
 * - baseURL: 请求的基础地址（通过 Vite 代理转发到后端）
 * - 请求拦截器：自动在请求头中注入 JWT Token
 * - 响应拦截器：统一处理错误（如 Token 过期）
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建 Axios 实例
const request = axios.create({
  baseURL: '/api',  // 所有请求自动加上 /api 前缀
  timeout: 30000,   // 请求超时时间 30 秒
})

// 请求拦截器：在每次请求发出前自动添加 Token
request.interceptors.request.use(
  (config) => {
    // 从 localStorage 中获取 Token
    const token = localStorage.getItem('token')
    if (token) {
      // 在请求头中添加 Authorization
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器：统一处理错误
request.interceptors.response.use(
  (response) => {
    // 请求成功，直接返回数据
    return response.data
  },
  (error) => {
    // 请求失败，根据状态码做不同处理
    if (error.response) {
      const { status, data } = error.response
      switch (status) {
        case 401:
          // Token 过期或无效 → 清除登录信息，跳转登录页
          localStorage.clear()
          ElMessage.error('登录已过期，请重新登录')
          // 动态 import 避免循环依赖，同时清空 Pinia Store
          setTimeout(async () => {
            const { useAuthStore } = await import('@/stores/auth')
            const { default: router } = await import('@/router')
            const auth = useAuthStore()
            auth.logout()
            router.push('/login')
          }, 1000)
          break
        case 403:
          ElMessage.error('没有权限执行此操作')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 409:
          ElMessage.error(data.detail || '资源冲突')
          break
        default:
          ElMessage.error(data.detail || `请求失败 (${status})`)
      }
    } else {
      // 网络错误（后端未启动等情况）
      ElMessage.error('网络连接失败，请检查后端服务是否启动')
    }
    return Promise.reject(error)
  }
)

export default request
