<template>
  <div class="users-management-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <h3>用户管理</h3>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            添加用户
          </el-button>
        </div>
      </template>

      <div class="toolbar">
        <el-input
          v-model="searchQuery"
          placeholder="搜索邮箱或昵称"
          clearable
          style="width: 300px"
          @clear="fetchUsers"
          @keyup.enter="fetchUsers"
        >
          <template #append>
            <el-button @click="fetchUsers">
              <el-icon><Search /></el-icon>
            </el-button>
          </template>
        </el-input>
      </div>

      <el-table :data="users" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="nickname" label="昵称" width="120">
          <template #default="{ row }">
            {{ row.nickname || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="tier" label="套餐" width="120">
          <template #default="{ row }">
            <el-tag :type="tierType(row.tier)">{{ row.tier }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="超级管理员" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_superuser ? 'danger' : 'info'">
              {{ row.is_superuser ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="warning" @click="handleResetPassword(row)">
              重置密码
            </el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchUsers"
          @current-change="fetchUsers"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑用户' : '添加用户'"
      width="500px"
      @close="resetForm"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="邮箱" prop="email" v-if="!isEdit">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="form.nickname" placeholder="请输入昵称" />
        </el-form-item>
        <el-form-item label="密码" prop="password" v-if="!isEdit">
          <el-input v-model="form.password" type="password" show-password placeholder="至少8位" />
        </el-form-item>
        <el-form-item label="套餐" prop="tier">
          <el-select v-model="form.tier" style="width: 100%">
            <el-option label="Free" value="free" />
            <el-option label="Pro" value="pro" />
            <el-option label="Enterprise" value="enterprise" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="Active" value="active" />
            <el-option label="Inactive" value="inactive" />
            <el-option label="Suspended" value="suspended" />
          </el-select>
        </el-form-item>
        <el-form-item label="超级管理员">
          <el-switch v-model="form.is_superuser" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { usersApi } from '@/api/users'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'

const authStore = useAuthStore()
const loading = ref(false)
const submitting = ref(false)
const users = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchQuery = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingUserId = ref(null)
const formRef = ref(null)

const form = reactive({
  email: '',
  nickname: '',
  password: '',
  tier: 'free',
  status: 'active',
  is_superuser: false,
})

const rules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少8位', trigger: 'blur' },
  ],
}

function tierType(tier) {
  const map = { free: 'info', pro: 'success', enterprise: 'warning' }
  return map[tier] || 'info'
}

function statusType(status) {
  const map = { active: 'success', inactive: 'info', suspended: 'danger' }
  return map[status] || 'info'
}

function formatTime(time) {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm') : '-'
}

async function fetchUsers() {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
    }
    if (searchQuery.value) {
      params.search = searchQuery.value
    }
    const res = await usersApi.list(params)
    users.value = res.items
    total.value = res.total
  } catch (e) {
  } finally {
    loading.value = false
  }
}

function handleAdd() {
  isEdit.value = false
  editingUserId.value = null
  dialogVisible.value = true
}

function handleEdit(row) {
  isEdit.value = true
  editingUserId.value = row.id
  form.email = row.email
  form.nickname = row.nickname || ''
  form.password = ''
  form.tier = row.tier
  form.status = row.status
  form.is_superuser = row.is_superuser
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isEdit.value) {
      await usersApi.update(editingUserId.value, {
        nickname: form.nickname,
        tier: form.tier,
        status: form.status,
        is_superuser: form.is_superuser,
      })
      ElMessage.success('用户更新成功')
    } else {
      await usersApi.create({
        email: form.email,
        nickname: form.nickname,
        password: form.password,
        tier: form.tier,
        status: form.status,
        is_superuser: form.is_superuser,
      })
      ElMessage.success('用户创建成功')
    }
    dialogVisible.value = false
    fetchUsers()
  } catch (e) {
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户 ${row.email} 吗？此操作不可恢复。`,
      '确认删除',
      { type: 'warning' }
    )
    await usersApi.delete(row.id)
    ElMessage.success('用户已删除')
    fetchUsers()
  } catch (e) {
    if (e !== 'cancel') {
    }
  }
}

async function handleResetPassword(row) {
  try {
    await ElMessageBox.confirm(
      `确定要重置用户 ${row.email} 的密码吗？新密码将显示在提示中。`,
      '重置密码',
      { type: 'warning' }
    )
    const res = await usersApi.resetPassword(row.id)
    ElMessage.success({
      message: res.message,
      duration: 10000,
    })
  } catch (e) {
    if (e !== 'cancel') {
    }
  }
}

function resetForm() {
  form.email = ''
  form.nickname = ''
  form.password = ''
  form.tier = 'free'
  form.status = 'active'
  form.is_superuser = false
  formRef.value?.resetFields()
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
.users-management-page {
  padding: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
}

.toolbar {
  margin-bottom: 16px;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
