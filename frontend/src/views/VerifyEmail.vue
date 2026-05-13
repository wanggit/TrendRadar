<template>
  <div class="verify-page">
    <el-card class="verify-card">
      <template #header>
        <h2>邮箱验证</h2>
      </template>

      <div v-if="status === 'loading'" class="status-content">
        <el-icon class="spinning"><Loading /></el-icon>
        <p>正在验证...</p>
      </div>

      <div v-else-if="status === 'success'" class="status-content">
        <el-icon class="success-icon"><CircleCheckFilled /></el-icon>
        <p>{{ message }}</p>
        <el-button type="primary" @click="$router.push('/login')">去登录</el-button>
      </div>

      <div v-else-if="status === 'error'" class="status-content">
        <el-icon class="error-icon"><CircleCloseFilled /></el-icon>
        <p>{{ message }}</p>
        <el-button type="primary" @click="$router.push('/login')">返回登录</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { authApi } from '@/api/auth'
import { Loading, CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const route = useRoute()
const status = ref('loading')
const message = ref('')

onMounted(async () => {
  const token = route.query.token
  if (!token) {
    status.value = 'error'
    message.value = '缺少验证令牌'
    return
  }

  try {
    const res = await authApi.verifyEmail(token)
    status.value = 'success'
    message.value = res.message || '邮箱验证成功'
  } catch (e) {
    status.value = 'error'
    message.value = e.response?.data?.detail || '验证失败，链接可能已过期'
  }
})
</script>

<style scoped>
.verify-page {
  min-height: 100vh;
  background: #f0f2f5;
  display: flex;
  align-items: center;
  justify-content: center;
}

.verify-card {
  width: 400px;
  text-align: center;
}

.verify-card h2 {
  margin: 0;
}

.status-content {
  padding: 30px 0;
}

.spinning {
  font-size: 48px;
  color: #409eff;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.success-icon {
  font-size: 48px;
  color: #67c23a;
}

.error-icon {
  font-size: 48px;
  color: #f56c6c;
}
</style>
