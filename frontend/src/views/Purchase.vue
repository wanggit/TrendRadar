<template>
  <div class="purchase-page">
    <el-card class="purchase-card">
      <template #header>
        <h2>购买专业版</h2>
      </template>

      <el-alert
        v-if="authStore.isTrialActive"
        :title="`试用剩余 ${authStore.trialDaysLeft} 天，试用结束后将降级为免费版`"
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 20px"
      />

      <div class="section">
        <h3>选择时长</h3>
        <div class="plans">
          <div
            v-for="plan in plans"
            :key="plan.type"
            class="plan-item"
            :class="{ selected: selectedPlan === plan.type }"
            @click="selectedPlan = plan.type"
          >
            <div class="plan-name">{{ plan.label }}</div>
            <div class="plan-price">¥{{ plan.price }}</div>
            <div class="plan-unit">{{ plan.unit }}</div>
            <div v-if="plan.discount" class="plan-discount">{{ plan.discount }}</div>
          </div>
        </div>
      </div>

      <div class="section">
        <h3>选择支付方式</h3>
        <div class="payment-methods">
          <div
            class="payment-item"
            :class="{ selected: selectedPayment === 'alipay' }"
            @click="selectedPayment = 'alipay'"
          >
            <el-icon><Money /></el-icon>
            <span>支付宝</span>
          </div>
          <div
            class="payment-item"
            :class="{ selected: selectedPayment === 'wxpay' }"
            @click="selectedPayment = 'wxpay'"
          >
            <el-icon><ChatDotRound /></el-icon>
            <span>微信支付</span>
          </div>
        </div>
      </div>

      <div class="summary">
        <div class="summary-row">
          <span>应付金额</span>
          <span class="amount">¥{{ currentPrice }}</span>
        </div>
      </div>

      <el-button
        type="primary"
        size="large"
        class="pay-btn"
        @click="handlePay"
        :loading="paying"
      >
        立即支付
      </el-button>
    </el-card>

    <el-dialog v-model="showPaymentDialog" title="正在支付" width="400px" :close-on-click-modal="false">
      <div class="payment-dialog-content">
        <div v-if="paymentStatus === 'pending'" class="pending-state">
          <el-icon class="spinning"><Loading /></el-icon>
          <p>等待支付完成...</p>
          <p class="hint">请在新打开的窗口中完成支付</p>
        </div>
        <div v-else-if="paymentStatus === 'success'" class="success-state">
          <el-icon class="success-icon"><CircleCheckFilled /></el-icon>
          <p>支付成功！已升级为专业版</p>
          <el-button type="primary" @click="goDashboard">返回仪表盘</el-button>
        </div>
        <div v-else-if="paymentStatus === 'failed'" class="failed-state">
          <el-icon class="failed-icon"><CircleCloseFilled /></el-icon>
          <p>支付失败，请重试</p>
          <el-button @click="showPaymentDialog = false">关闭</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { paymentApi } from '@/api/payment'
import { Money, ChatDotRound, Loading, CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

const plans = [
  { type: 'monthly', label: '月卡', price: 49, unit: '/30天' },
  { type: 'quarterly', label: '季卡', price: 129, unit: '/90天', discount: '省 ¥18' },
  { type: 'yearly', label: '年卡', price: 399, unit: '/365天', discount: '省 ¥189' },
]

const selectedPlan = ref('monthly')
const selectedPayment = ref('alipay')
const paying = ref(false)
const showPaymentDialog = ref(false)
const paymentStatus = ref('pending')
let pollingTimer = null
let currentOrderId = null

const currentPrice = computed(() => {
  const plan = plans.find(p => p.type === selectedPlan.value)
  return plan ? plan.price : 0
})

async function handlePay() {
  paying.value = true
  try {
    const res = await paymentApi.createOrder({
      product_type: selectedPlan.value,
      payment_method: selectedPayment.value,
    })

    currentOrderId = res.order_id
    window.open(res.payment_url, '_blank')

    showPaymentDialog.value = true
    paymentStatus.value = 'pending'
    startPolling(res.order_id)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建订单失败')
  } finally {
    paying.value = false
  }
}

function startPolling(orderId) {
  pollingTimer = setInterval(async () => {
    try {
      const res = await paymentApi.getOrderStatus(orderId)
      if (res.status === 'paid') {
        paymentStatus.value = 'success'
        stopPolling()
        await authStore.fetchUser()
      }
    } catch {
    }
  }, 3000)
}

function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

function goDashboard() {
  showPaymentDialog.value = false
  router.push('/dashboard')
}

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.purchase-page {
  min-height: 100vh;
  background: #f0f2f5;
  padding: 40px 20px;
  display: flex;
  justify-content: center;
}

.purchase-card {
  width: 100%;
  max-width: 600px;
}

.purchase-card h2 {
  margin: 0;
  font-size: 22px;
}

.section {
  margin-bottom: 24px;
}

.section h3 {
  font-size: 16px;
  color: #303133;
  margin-bottom: 12px;
}

.plans {
  display: flex;
  gap: 12px;
}

.plan-item {
  flex: 1;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.plan-item:hover {
  border-color: #409eff;
}

.plan-item.selected {
  border-color: #409eff;
  background: #ecf5ff;
}

.plan-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
}

.plan-price {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
}

.plan-unit {
  font-size: 13px;
  color: #909399;
}

.plan-discount {
  position: absolute;
  top: -8px;
  right: -8px;
  background: #f56c6c;
  color: #fff;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
}

.payment-methods {
  display: flex;
  gap: 12px;
}

.payment-item {
  flex: 1;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 16px;
  transition: all 0.2s;
}

.payment-item:hover {
  border-color: #409eff;
}

.payment-item.selected {
  border-color: #409eff;
  background: #ecf5ff;
}

.summary {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
}

.amount {
  font-size: 28px;
  font-weight: bold;
  color: #f56c6c;
}

.pay-btn {
  width: 100%;
}

.payment-dialog-content {
  text-align: center;
  padding: 20px 0;
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

.failed-icon {
  font-size: 48px;
  color: #f56c6c;
}

.hint {
  color: #909399;
  font-size: 14px;
}
</style>
