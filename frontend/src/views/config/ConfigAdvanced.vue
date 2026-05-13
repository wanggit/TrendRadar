<template>
  <div>
    <div class="module-header">
      <h3>高级设置</h3>
    </div>

    <el-alert
      title="高级设置包含调试模式、爬虫参数和权重配置，请谨慎修改"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    />

    <el-form :model="form" label-width="160px" style="max-width: 650px">
      <el-divider content-position="left">调试</el-divider>

      <el-form-item label="调试模式">
        <el-switch v-model="form.debug" />
        <span style="color: #909399; font-size: 12px; margin-left: 8px">开启后输出详细日志</span>
      </el-form-item>

      <el-divider content-position="left">爬虫参数</el-divider>

      <el-form-item label="请求间隔 (秒)">
        <el-input-number v-model="form.crawler.request_interval" :min="0" :max="60" style="width: 120px" />
        <span style="color: #909399; font-size: 12px; margin-left: 8px">每次请求之间的等待时间</span>
      </el-form-item>

      <el-form-item label="启用代理">
        <el-switch v-model="form.crawler.use_proxy" />
      </el-form-item>

      <el-form-item label="默认代理" v-if="form.crawler.use_proxy">
        <el-input v-model="form.crawler.default_proxy" placeholder="例如: http://127.0.0.1:7890" style="width: 300px" />
      </el-form-item>

      <el-divider content-position="left">权重配置</el-divider>

      <el-form-item label="排名权重">
        <el-input-number v-model="form.weight.rank" :min="0" :max="10" :step="0.1" :precision="1" style="width: 120px" />
        <span style="color: #909399; font-size: 12px; margin-left: 8px">排名在最终评分中的权重</span>
      </el-form-item>

      <el-form-item label="关键词权重">
        <el-input-number v-model="form.weight.frequency" :min="0" :max="10" :step="0.1" :precision="1" style="width: 120px" />
        <span style="color: #909399; font-size: 12px; margin-left: 8px">关键词匹配在最终评分中的权重</span>
      </el-form-item>

      <el-form-item label="热度权重">
        <el-input-number v-model="form.weight.hotness" :min="0" :max="10" :step="0.1" :precision="1" style="width: 120px" />
        <span style="color: #909399; font-size: 12px; margin-left: 8px">热度值在最终评分中的权重</span>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="save" :loading="saving">保存</el-button>
        <el-button @click="reset">重置</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { configApi } from '@/api/config'
import { ElMessage } from 'element-plus'

const saving = ref(false)

const form = reactive({
  debug: false,
  crawler: {
    request_interval: 1,
    use_proxy: false,
    default_proxy: '',
  },
  weight: {
    rank: 1.0,
    frequency: 1.0,
    hotness: 1.0,
  },
})

let originalConfig = null

onMounted(async () => {
  await loadConfig()
})

async function loadConfig() {
  const config = await configApi.getFullConfig()
  const adv = config.advanced || {}
  Object.assign(form, {
    debug: adv.debug || false,
    crawler: {
      request_interval: adv.crawler?.request_interval || 1,
      use_proxy: adv.crawler?.use_proxy || false,
      default_proxy: adv.crawler?.default_proxy || '',
    },
    weight: {
      rank: adv.weight?.rank || 1.0,
      frequency: adv.weight?.frequency || 1.0,
      hotness: adv.weight?.hotness || 1.0,
    },
  })
  originalConfig = JSON.parse(JSON.stringify(form))
}

async function save() {
  saving.value = true
  try {
    const config = await configApi.getFullConfig()
    config.advanced = JSON.parse(JSON.stringify(form))
    await configApi.updateFullConfig(config)
    ElMessage.success('高级设置已保存')
    originalConfig = JSON.parse(JSON.stringify(form))
  } finally {
    saving.value = false
  }
}

function reset() {
  Object.assign(form, JSON.parse(JSON.stringify(originalConfig)))
  ElMessage.info('已重置为上次保存的配置')
}
</script>

<style scoped>
.module-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.module-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}
</style>
