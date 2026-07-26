import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
      meta: { guest: true }
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/Register.vue'),
      meta: { guest: true }
    },
    {
      path: '/',
      redirect: '/chat'
    },
    {
      path: '/chat',
      name: 'chat',
      component: () => import('@/views/Chat.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/chat/:id',
      name: 'chat-detail',
      component: () => import('@/views/Chat.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/admin/knowledge',
      name: 'knowledge-base',
      component: () => import('@/views/KnowledgeBase.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/Profile.vue'),
      meta: { requiresAuth: true }
    },
  ],
})

// 导航守卫：控制页面访问权限
router.beforeEach((to, from, next) => {
  const auth = useAuthStore()

  // 需要登录的页面 → 未登录时跳转登录页
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    next('/login')
    return
  }

  // 游客页面（登录/注册） → 已登录时跳转首页
  if (to.meta.guest && auth.isLoggedIn) {
    next('/chat')
    return
  }

  // 管理员页面 → 非管理员跳转首页
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    next('/chat')
    return
  }

  next()
})

export default router
