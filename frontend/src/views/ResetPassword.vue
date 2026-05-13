<template>
  <div class="reset-page">
    <el-card class="reset-card">
      <template #header>
        <h2>重置密码</h2>
      </template>

      <div v-if="!token" class="forgot-form">
        <p>输入您的注册邮箱，我们将发送密码重置链接</p>
        <el-form @submit.prevent="handleForgot">
          <el-form-item>
            <el-input v-model="email" type="email" placeholder="请输入邮箱" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleForgot" :loading="sending" style="width: 100%">
              发送重置链接
            </el-button>
          </el-form-item>
        </el-form>
        <div v-if="forgotSent" class="success-msg">
          <el-alert title="重置链接已发送，请检查邮箱" type="success" :closable="false" />
        </div>
      </div>

      <div v-else class="reset-form">
        <el-form @submit.prevent="handleReset">
          <el-form-item>
            <el-input v-model="newPassword" type="password" placeholder="新密码（至少8位）" show-password />
          </el-form-item>
          <el-form-item>
            <el-input v-model="confirmPassword" type="password" placeholder="确认新密码" show-password />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleReset" :loading="resetting" style="width: 100%">
              重置密码
            </el-button>
          </el-form-item>
        </el-form>
        <div v-if="resetSuccess" class="success-msg">
          <el-alert title="密码重置成功" type="success" :closable="false" />
          <el-button type="primary" @click="$router.push('/login')" style="margin-top: 12px">
            去登录
          </el-button>
        </div>
      </div>

      <div class="back-link">
        <router-link to="/login">返回登录</router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authApi } from '@/api/auth'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const token = route.query.token || ''

const email = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const sending = ref(false)
const resetting = ref(false)
const forgotSent = ref(false)
const resetSuccess = ref(false)

async function handleForgot() {
  if (!email.value) {
    ElMessage.warning('请输入邮箱')
    return
  }
  sending.value = true
  try {
    await authApi.forgotPassword({ email: email.value })
    forgotSent.value = true
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '发送失败')
  } finally {
    sending.value = false
  }
}

async function handleReset() {
  if (newPassword.value.length < 8) {
    ElMessage.warning('密码至少8位')
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    ElMessage.warning('两次密码不一致')
    return
  }
  resetting.value = true
  try {
    await authApi.resetPassword(token, newPassword.value)
    resetSuccess.value = true
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '重置失败')
  } finally {
    resetting.value = false
  }
}
</script>

<style scoped>
.reset-page {
  min-height: 100vh;
  background: #f0f2f5;
  display: flex;
  align-items: center;
  justify-content: center;
}

.reset-card {
  width: 400px;
}

.reset-card h2 {
  margin: 0;
}

.success-msg {
  margin-top: 12px;
}

.back-link {
  text-align: center;
  margin-top: 16px;
}

.back-link a {
  color: #409eff;
  text-decoration: none;
}
</style>
