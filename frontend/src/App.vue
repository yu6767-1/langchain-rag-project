<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter, useRoute } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

// 应用初始化：验证 token 是否仍然有效
onMounted(async () => {
  if (auth.isLoggedIn) {
    const valid = await auth.checkAuth()
    if (!valid) {
      router.push('/login')
    }
  }
})

// 是否折叠侧边栏
const isCollapse = ref(false)

// 当前激活的菜单项
const activeMenu = computed(() => {
  if (route.path.startsWith('/chat')) return '/chat'
  if (route.path.startsWith('/admin')) return '/admin/knowledge'
  if (route.path.startsWith('/profile')) return '/profile'
  return route.path
})

function handleMenuSelect(index) {
  router.push(index)
}

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div id="app-container">
    <!-- 未登录状态：全屏展示登录/注册页 -->
    <div v-if="!auth.isLoggedIn" class="guest-wrapper">
      <router-view />
    </div>

    <!-- 已登录状态：左边栏 + 右侧内容 -->
    <el-container v-else class="layout-container">
      <!-- ========== 左侧边栏 ========== -->
      <el-aside :width="isCollapse ? '64px' : '220px'" class="app-sidebar">
        <!-- Logo 区域 -->
        <div class="sidebar-logo" @click="router.push('/chat')">
          <span class="logo-icon">📚</span>
          <span v-show="!isCollapse" class="logo-text">知识库问答系统</span>
        </div>

        <el-divider style="margin: 0" />

        <!-- 导航菜单 -->
        <el-menu
          :default-active="activeMenu"
          :collapse="isCollapse"
          :collapse-transition="false"
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409eff"
          class="sidebar-menu"
          @select="handleMenuSelect"
        >
          <el-menu-item index="/chat">
            <el-icon><ChatDotRound /></el-icon>
            <template #title>智能问答</template>
          </el-menu-item>

          <el-menu-item v-if="auth.isAdmin" index="/admin/knowledge">
            <el-icon><FolderOpened /></el-icon>
            <template #title>知识库管理</template>
          </el-menu-item>

          <el-menu-item index="/profile">
            <el-icon><User /></el-icon>
            <template #title>个人中心</template>
          </el-menu-item>
        </el-menu>

        <!-- 底部用户信息 -->
        <div class="sidebar-footer">
          <el-divider style="margin: 0 0 12px 0" />
          <div class="sidebar-user">
            <el-avatar :size="32" icon="UserFilled" />
            <div v-show="!isCollapse" class="user-text">
              <div class="user-name">{{ auth.username }}</div>
              <div class="user-role">{{ auth.isAdmin ? '管理员' : '普通用户' }}</div>
            </div>
          </div>
          <el-button
            v-show="!isCollapse"
            text
            size="small"
            style="color: #bfcbd9; width: 100%; margin-top: 8px"
            @click="handleLogout"
          >
            <el-icon><SwitchButton /></el-icon> 退出登录
          </el-button>
          <el-button
            v-show="isCollapse"
            text
            size="small"
            style="color: #bfcbd9; width: 100%; margin-top: 8px"
            @click="handleLogout"
          >
            <el-icon><SwitchButton /></el-icon>
          </el-button>

          <!-- 折叠按钮 -->
          <div class="collapse-btn" @click="isCollapse = !isCollapse">
            <el-icon>
              <Fold v-if="!isCollapse" />
              <Expand v-else />
            </el-icon>
          </div>
        </div>
      </el-aside>

      <!-- ========== 右侧内容区 ========== -->
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<style>
/* ========== 全局样式重置 ========== */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #f5f7fa;
  color: #333;
}

/* ========== 根容器 ========== */
#app-container {
  height: 100vh;
  overflow: hidden;
}

/* ========== 未登录时的全屏背景 ========== */
.guest-wrapper {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* ========== 整体布局 ========== */
.layout-container {
  height: 100vh;
}

/* ========== 左侧边栏 ========== */
.app-sidebar {
  background-color: #304156 !important;
  display: flex !important;
  flex-direction: column;
  transition: width 0.3s;
  overflow: hidden;
}

.sidebar-logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  cursor: pointer;
  padding: 0 16px;
  flex-shrink: 0;
}

.logo-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
}

/* 侧边栏菜单 */
.sidebar-menu {
  flex: 1;
  border-right: none !important;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-menu .el-menu-item {
  height: 50px;
  line-height: 50px;
}

.sidebar-menu .el-menu-item:hover {
  background-color: rgba(255, 255, 255, 0.06) !important;
}

.sidebar-menu .el-menu-item.is-active {
  background-color: rgba(64, 158, 255, 0.15) !important;
}

/* 底部用户区 */
.sidebar-footer {
  flex-shrink: 0;
  padding: 0 16px 12px;
}

.sidebar-footer .el-divider--horizontal {
  border-top-color: rgba(255, 255, 255, 0.1);
}

.sidebar-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
}

.user-text {
  min-width: 0;
}

.user-name {
  font-size: 14px;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  font-size: 12px;
  color: #909399;
}

/* 折叠按钮 */
.collapse-btn {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 8px 0 0;
  cursor: pointer;
  color: #bfcbd9;
  font-size: 18px;
  transition: color 0.2s;
}

.collapse-btn:hover {
  color: #409eff;
}

/* ========== 右侧主内容区 ========== */
.app-main {
  padding: 0 !important;
  overflow: hidden;
  background: #f5f7fa;
}
</style>
