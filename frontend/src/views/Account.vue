<template>
  <div class="account-page">
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card>
          <template #header>账户信息</template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="邮箱">{{ authStore.user?.email }}</el-descriptions-item>
            <el-descriptions-item label="昵称">{{ authStore.user?.nickname || '-' }}</el-descriptions-item>
            <el-descriptions-item label="套餐">
              <el-tag :type="tierType">{{ authStore.user?.tier }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="authStore.user?.status === 'active' ? 'success' : 'danger'">
                {{ authStore.user?.status }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="注册时间">
              {{ formatTime(authStore.user?.created_at) }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>修改密码</template>
          <el-form :model="passwordForm" :rules="passwordRules" ref="formRef" label-width="100px">
            <el-form-item label="当前密码" prop="old_password">
              <el-input v-model="passwordForm.old_password" type="password" show-password />
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input v-model="passwordForm.new_password" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleUpdatePassword" :loading="loading">
                更新密码
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const authStore = useAuthStore()
const formRef = ref(null)
const loading = ref(false)

const tierType = computed(() => {
  const map = { free: 'info', pro: 'success', enterprise: 'warning' }
  return map[authStore.user?.tier] || 'info'
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
})

const passwordRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 8, message: '密码至少 8 位', trigger: 'blur' }],
}

async function handleUpdatePassword() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  loading.value = true
  try {
    await authApi.changePassword(passwordForm)
    ElMessage.success('密码更新成功')
    passwordForm.old_password = ''
    passwordForm.new_password = ''
  } catch (e) {
  } finally {
    loading.value = false
  }
}

function formatTime(time) {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm') : '-'
}
</script>

<style scoped>
.account-page {
  padding: 10px;
}
</style>
