/**
 * 认证状态管理
 * =============
 * 使用 Pinia 管理用户登录状态。
 * Pinia 是 Vue 3 官方推荐的状态管理库，类似于 Vuex 但更简洁。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, register as registerApi, getCurrentUser } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  // ===== 状态 =====
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')
  const role = ref(localStorage.getItem('role') || '')

  // ===== 计算属性 =====
  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => role.value === 'admin')

  // ===== 方法 =====

  /**
   * 登录
   */
  async function login(usernameInput, password) {
    const res = await loginApi(usernameInput, password)
    token.value = res.access_token
    username.value = res.username
    role.value = res.role

    // 持久化存储（刷新页面后仍保留登录状态）
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('username', res.username)
    localStorage.setItem('role', res.role)

    return res
  }

  /**
   * 注册
   */
  async function register(usernameInput, password) {
    return await registerApi(usernameInput, password)
  }

  /**
   * 退出登录
   */
  function logout() {
    token.value = ''
    username.value = ''
    role.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('role')
  }

  /**
   * 验证 Token 是否有效，并同步用户信息（页面加载时调用）
   */
  async function checkAuth() {
    if (!token.value) return false
    try {
      const user = await getCurrentUser()
      // 用服务器返回的最新数据同步本地状态
      username.value = user.username
      role.value = user.role
      localStorage.setItem('username', user.username)
      localStorage.setItem('role', user.role)
      return true
    } catch {
      logout()
      return false
    }
  }

  return {
    token,
    username,
    role,
    isLoggedIn,
    isAdmin,
    login,
    register,
    logout,
    checkAuth,
  }
})
