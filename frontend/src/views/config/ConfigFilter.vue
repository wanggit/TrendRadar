<template>
  <div>
    <div class="module-header">
      <h3>筛选策略</h3>
    </div>

    <el-alert
      title="筛选策略决定了如何从抓取的数据中过滤出你感兴趣的内容"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    />

    <el-form :model="form" label-width="160px" style="max-width: 600px">
      <el-form-item label="筛选方法">
        <el-select v-model="form.method" style="width: 200px">
          <el-option label="keyword - 关键词匹配" value="keyword" />
          <el-option label="ai - AI 智能筛选" value="ai" />
        </el-select>
        <div style="color: #909399; font-size: 12px; margin-left: 8px; margin-top: 4px">
          <span v-if="form.method === 'keyword'">使用 frequency_words.txt 进行关键词匹配</span>
          <span v-else>使用 AI 模型 + ai_interests.txt 进行智能筛选</span>
        </div>
      </el-form-item>

      <el-form-item label="按标签优先级排序" v-if="form.method === 'ai'">
        <el-switch v-model="form.priority_sort_enabled" />
        <span style="color: #909399; font-size: 12px; margin-left: 8px">开启后按 AI 标签的优先级排序结果</span>
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
  method: 'keyword',
  priority_sort_enabled: false,
})

let originalConfig = null

onMounted(async () => {
  await loadConfig()
})

async function loadConfig() {
  const config = await configApi.getFullConfig()
  const filter = config.filter_strategy || config.filter || {}
  Object.assign(form, {
    method: filter.method || 'keyword',
    priority_sort_enabled: filter.priority_sort_enabled || false,
  })
  originalConfig = { ...form }
}

async function save() {
  saving.value = true
  try {
    const config = await configApi.getFullConfig()
    config.filter_strategy = { ...form }
    config.filter = { ...form }
    await configApi.updateFullConfig(config)
    ElMessage.success('筛选策略已保存')
    originalConfig = { ...form }
  } finally {
    saving.value = false
  }
}

function reset() {
  Object.assign(form, originalConfig)
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
