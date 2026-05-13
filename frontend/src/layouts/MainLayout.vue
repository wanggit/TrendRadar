<template>
  <el-container class="main-layout">
    <el-aside width="220px">
      <div class="logo">
        <h2>TrendRadar</h2>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/config">
          <el-icon><Setting /></el-icon>
          <span>配置管理</span>
        </el-menu-item>
        <el-menu-item index="/news">
          <el-icon><Document /></el-icon>
          <span>新闻浏览</span>
        </el-menu-item>
        <el-menu-item index="/tasks">
          <el-icon><Timer /></el-icon>
          <span>任务调度</span>
        </el-menu-item>
        <el-menu-item index="/task-history">
          <el-icon><List /></el-icon>
          <span>任务历史</span>
        </el-menu-item>
        <el-menu-item index="/users" v-if="authStore.user?.is_superuser">
          <el-icon><UserFilled /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/account">
          <el-icon><User /></el-icon>
          <span>账户设置</span>
        </el-menu-item>
        <el-menu-item index="/orders">
          <el-icon><Tickets /></el-icon>
          <span>订单记录</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-tag v-if="authStore.user?.tier === 'pro'" type="success" size="small" effect="dark">
            PRO
          </el-tag>
          <el-tag v-else type="info" size="small">
            FREE
          </el-tag>
          <span v-if="authStore.isTrialActive" class="trial-countdown" :class="{ warning: authStore.isTrialExpiringSoon }">
            试用剩余 {{ authStore.trialDaysLeft }} 天
          </span>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              {{ authStore.user?.nickname || authStore.user?.email }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="account">账户设置</el-dropdown-item>
                <el-dropdown-item command="orders">订单记录</el-dropdown-item>
                <el-dropdown-item command="pricing">定价方案</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <el-main class="content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { useAuthStore } from '@/stores/auth'
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const authStore = useAuthStore()

onMounted(() => {
  if (!authStore.user) {
    authStore.fetchUser()
  }
})

function handleCommand(command) {
  if (command === 'logout') {
    authStore.logout()
  } else if (command === 'account') {
    router.push('/account')
  } else if (command === 'orders') {
    router.push('/orders')
  } else if (command === 'pricing') {
    router.push('/pricing')
  }
}
</script>

<style scoped>
.main-layout {
  height: 100vh;
}

.el-aside {
  background-color: #304156;
  color: #fff;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #263445;
  color: #fff;
}

.logo h2 {
  margin: 0;
  font-size: 18px;
}

.header {
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.trial-countdown {
  font-size: 13px;
  color: #67c23a;
  font-weight: 500;
}

.trial-countdown.warning {
  color: #e6a23c;
}

.user-info {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
}

.content {
  background-color: #f0f2f5;
  padding: 20px;
}
</style>
