<template>
  <div class="orders-page">
    <el-card>
      <template #header>
        <h2>订单历史</h2>
      </template>

      <el-table :data="orders" style="width: 100%" v-loading="loading">
        <el-table-column prop="order_no" label="订单号" width="220" />
        <el-table-column label="产品" width="100">
          <template #default="{ row }">
            {{ productLabels[row.product_type] }}
          </template>
        </el-table-column>
        <el-table-column label="金额" width="100">
          <template #default="{ row }">
            ¥{{ row.amount }}
          </template>
        </el-table-column>
        <el-table-column label="支付方式" width="100">
          <template #default="{ row }">
            {{ paymentLabels[row.payment_method] }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTypes[row.status]">
              {{ statusLabels[row.status] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="支付时间" width="180">
          <template #default="{ row }">
            {{ row.paid_at ? formatDate(row.paid_at) : '-' }}
          </template>
        </el-table-column>
      </el-table>

      <div v-if="!loading && orders.length === 0" class="empty">
        <el-empty description="暂无订单记录" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { paymentApi } from '@/api/payment'
import { ElMessage } from 'element-plus'

const orders = ref([])
const loading = ref(true)

const productLabels = {
  monthly: '月卡',
  quarterly: '季卡',
  yearly: '年卡',
}

const paymentLabels = {
  alipay: '支付宝',
  wxpay: '微信支付',
}

const statusLabels = {
  pending: '待支付',
  paid: '已支付',
  failed: '已失败',
  expired: '已过期',
}

const statusTypes = {
  pending: 'warning',
  paid: 'success',
  failed: 'danger',
  expired: 'info',
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(async () => {
  try {
    const res = await paymentApi.getOrders()
    orders.value = res.items
  } catch (e) {
    ElMessage.error('加载订单失败')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.orders-page {
  padding: 20px;
}

.orders-page h2 {
  margin: 0;
  font-size: 20px;
}

.empty {
  padding: 40px 0;
}
</style>
