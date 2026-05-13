<template>
  <div class="pricing-page">
    <div class="pricing-header">
      <h1>选择适合您的方案</h1>
      <p class="subtitle">7 天免费试用专业版所有功能，无需信用卡</p>
    </div>

    <div class="pricing-cards">
      <div class="pricing-card">
        <div class="card-header">
          <h2>免费版</h2>
          <div class="price">¥0<span>/月</span></div>
        </div>
        <ul class="features">
          <li><el-icon><Check /></el-icon> 最多 3 个热榜平台</li>
          <li><el-icon><Check /></el-icon> 5 个关键词组</li>
          <li><el-icon><Check /></el-icon> 每日 4 次推送</li>
          <li><el-icon><Check /></el-icon> 1 个推送渠道</li>
          <li><el-icon><Close /></el-icon> <span class="disabled">AI 深度分析</span></li>
          <li><el-icon><Close /></el-icon> <span class="disabled">AI 智能筛选</span></li>
          <li><el-icon><Close /></el-icon> <span class="disabled">AI 翻译</span></li>
          <li><el-icon><Check /></el-icon> 7 天数据保留</li>
        </ul>
        <el-button size="large" class="card-btn" @click="handleFree">
          {{ isFree ? '当前方案' : '免费开始' }}
        </el-button>
      </div>

      <div class="pricing-card pro">
        <div class="pro-badge">推荐</div>
        <div class="card-header">
          <h2>专业版</h2>
          <div class="price">¥49<span>/月</span></div>
        </div>
        <ul class="features">
          <li><el-icon><Check /></el-icon> 最多 15 个热榜平台</li>
          <li><el-icon><Check /></el-icon> 无限关键词组</li>
          <li><el-icon><Check /></el-icon> 每日 48 次推送</li>
          <li><el-icon><Check /></el-icon> 3 个推送渠道</li>
          <li><el-icon><Check /></el-icon> AI 深度分析</li>
          <li><el-icon><Check /></el-icon> AI 智能筛选</li>
          <li><el-icon><Check /></el-icon> AI 翻译</li>
          <li><el-icon><Check /></el-icon> 30 天数据保留</li>
          <li><el-icon><Check /></el-icon> 优先任务队列</li>
        </ul>
        <el-button type="primary" size="large" class="card-btn" @click="handlePro">
          {{ isPro ? '当前方案' : '立即购买' }}
        </el-button>
      </div>
    </div>

    <div class="pricing-footer">
      <p>所有方案均包含 7 天免费试用 · 随时可取消</p>
    </div>

    <AppFooter />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Check, Close } from '@element-plus/icons-vue'
import AppFooter from '@/components/Footer.vue'

const router = useRouter()
const authStore = useAuthStore()

const isFree = computed(() => authStore.user?.tier === 'free')
const isPro = computed(() => authStore.user?.tier === 'pro')

function handleFree() {
  if (!authStore.token) {
    router.push('/register')
  } else if (isFree.value) {
    router.push('/dashboard')
  }
}

function handlePro() {
  if (!authStore.token) {
    router.push('/login?redirect=/purchase')
  } else {
    router.push('/purchase')
  }
}
</script>

<style scoped>
.pricing-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 60px 20px;
}

.pricing-header {
  text-align: center;
  margin-bottom: 50px;
}

.pricing-header h1 {
  color: #fff;
  font-size: 36px;
  margin-bottom: 12px;
}

.subtitle {
  color: rgba(255, 255, 255, 0.85);
  font-size: 18px;
}

.pricing-cards {
  display: flex;
  justify-content: center;
  gap: 30px;
  max-width: 800px;
  margin: 0 auto;
  flex-wrap: wrap;
}

.pricing-card {
  background: #fff;
  border-radius: 16px;
  padding: 40px 30px;
  width: 340px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
  position: relative;
  transition: transform 0.3s;
}

.pricing-card:hover {
  transform: translateY(-5px);
}

.pricing-card.pro {
  border: 2px solid #409eff;
}

.pro-badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: #409eff;
  color: #fff;
  padding: 4px 16px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
}

.card-header h2 {
  font-size: 24px;
  margin: 0 0 16px 0;
  color: #303133;
}

.price {
  font-size: 42px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 30px;
}

.price span {
  font-size: 16px;
  font-weight: normal;
  color: #909399;
}

.features {
  list-style: none;
  padding: 0;
  margin: 0 0 30px 0;
}

.features li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  color: #606266;
  font-size: 15px;
}

.features li .el-icon {
  color: #67c23a;
}

.features li .disabled {
  color: #c0c4cc;
}

.features li .el-icon.is-close {
  color: #c0c4cc;
}

.card-btn {
  width: 100%;
}

.pricing-footer {
  text-align: center;
  margin-top: 40px;
  color: rgba(255, 255, 255, 0.7);
}
</style>
