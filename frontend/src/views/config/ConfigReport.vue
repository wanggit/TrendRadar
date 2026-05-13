<template>
  <div>
    <div class="module-header">
      <h3>报告模式</h3>
    </div>

    <el-alert
      title="报告模式决定了推送内容的聚合方式"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    />

    <el-form :model="form" label-width="160px" style="max-width: 600px">
      <el-form-item label="报告模式">
        <el-select v-model="form.mode" style="width: 200px">
          <el-option label="current - 当前快照" value="current">
            <span>current</span>
            <span style="color: #909399; margin-left: 8px; font-size: 12px">仅推送当前时刻的热榜</span>
          </el-option>
          <el-option label="daily - 每日汇总" value="daily">
            <span>daily</span>
            <span style="color: #909399; margin-left: 8px; font-size: 12px">推送当天累计的热榜汇总</span>
          </el-option>
          <el-option label="incremental - 增量推送" value="incremental">
            <span>incremental</span>
            <span style="color: #909399; margin-left: 8px; font-size: 12px">仅推送自上次以来的新增内容</span>
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="分组维度">
        <el-select v-model="form.display_mode" style="width: 200px">
          <el-option label="keyword - 按关键词分组" value="keyword" />
          <el-option label="platform - 按平台分组" value="platform" />
        </el-select>
      </el-form-item>

      <el-form-item label="按定义顺序排序">
        <el-switch v-model="form.sort_by_position_first" />
        <span style="color: #909399; font-size: 12px; margin-left: 8px">开启后按关键词定义顺序排列，而非热度</span>
      </el-form-item>

      <el-form-item label="排名高亮阈值">
        <el-input-number v-model="form.rank_threshold" :min="1" :max="100" style="width: 120px" />
        <span style="color: #909399; font-size: 12px; margin-left: 8px">排名在此数值内的条目会被高亮</span>
      </el-form-item>

      <el-form-item label="每关键词最大数量">
        <el-input-number v-model="form.max_news_per_keyword" :min="1" :max="50" style="width: 120px" />
        <span style="color: #909399; font-size: 12px; margin-left: 8px">每个关键词最多显示多少条新闻</span>
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
  mode: 'current',
  display_mode: 'keyword',
  sort_by_position_first: false,
  rank_threshold: 10,
  max_news_per_keyword: 10,
})

let originalConfig = null

onMounted(async () => {
  await loadConfig()
})

async function loadConfig() {
  const config = await configApi.getFullConfig()
  const report = config.report || {}
  Object.assign(form, {
    mode: report.mode || 'current',
    display_mode: report.display_mode || 'keyword',
    sort_by_position_first: report.sort_by_position_first || false,
    rank_threshold: report.rank_threshold || 10,
    max_news_per_keyword: report.max_news_per_keyword || 10,
  })
  originalConfig = { ...form }
}

async function save() {
  saving.value = true
  try {
    const config = await configApi.getFullConfig()
    config.report = { ...form }
    await configApi.updateFullConfig(config)
    ElMessage.success('报告模式已保存')
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
