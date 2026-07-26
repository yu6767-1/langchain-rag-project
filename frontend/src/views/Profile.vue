<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { changePassword } from '@/api/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const auth = useAuthStore()

const form = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})
const loading = ref(false)

async function handleChangePassword() {
  if (!form.value.oldPassword || !form.value.newPassword) {
    ElMessage.warning('请填写完整信息')
    return
  }
  if (form.value.newPassword.length < 6) {
    ElMessage.warning('新密码至少6位')
    return
  }
  if (form.value.newPassword !== form.value.confirmPassword) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  loading.value = true
  try {
    await changePassword(form.value.oldPassword, form.value.newPassword)
    ElMessage.success('密码修改成功，请重新登录')
    auth.logout()
    router.push('/login')
  } catch {
    // 错误已在拦截器中处理
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="profile-container">
    <el-card class="profile-card">
      <template #header>
        <h2>👤 个人中心</h2>
      </template>

      <!-- 用户信息 -->
      <el-descriptions title="基本信息" :column="2" border>
        <el-descriptions-item label="用户名">{{ auth.username }}</el-descriptions-item>
        <el-descriptions-item label="角色">
          <el-tag :type="auth.isAdmin ? 'danger' : 'info'" size="small">
            {{ auth.isAdmin ? '管理员' : '普通用户' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <!-- 修改密码 -->
      <el-divider />
      <h3>🔒 修改密码</h3>
      <el-form
        :model="form"
        label-width="100px"
        style="max-width: 460px; margin-top: 20px;"
      >
        <el-form-item label="原密码">
          <el-input
            v-model="form.oldPassword"
            type="password"
            placeholder="请输入原密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input
            v-model="form.newPassword"
            type="password"
            placeholder="至少6位新密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="再次输入新密码"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleChangePassword">
            修改密码
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.profile-container {
  padding: 24px;
  max-width: 720px;
  margin: 0 auto;
  height: 100%;
  overflow-y: auto;
}

.profile-card h2 {
  margin: 0;
  font-size: 20px;
}

.profile-card h3 {
  font-size: 16px;
  color: #606266;
}
</style>
