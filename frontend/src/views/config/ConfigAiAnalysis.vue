<template>
  <div>
    <div class="module-header">
      <h3>AI 分析功能</h3>
    </div>

    <el-alert
      title="AI 分析功能对抓取到的新闻进行智能分析和总结，生成分析报告"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    />

    <el-form :model="form" label-width="180px" style="max-width: 1100px">
      <el-form-item label="开启 AI 分析">
        <el-switch v-model="form.enabled" />
      </el-form-item>

      <el-form-item label="输出语言">
        <el-input v-model="form.language" placeholder="例如: 中文" style="width: 200px" />
      </el-form-item>

      <el-form-item label="分析模式">
        <el-select v-model="form.mode" style="width: 200px">
          <el-option label="follow_report - 跟随报告模式" value="follow_report" />
          <el-option label="daily - 每日分析" value="daily" />
          <el-option label="current - 当前分析" value="current" />
          <el-option label="incremental - 增量分析" value="incremental" />
        </el-select>
      </el-form-item>

      <el-form-item label="最大分析条数">
        <el-input-number v-model="form.max_news_for_analysis" :min="1" :max="500" style="width: 120px" />
      </el-form-item>

      <el-divider content-position="left">分析提示词</el-divider>

      <el-form-item label="提示词内容">
        <el-input
          v-model="form.prompt_content"
          type="textarea"
          :rows="20"
          placeholder="请输入 AI 分析提示词，支持 [system] 和 [user] 标记分隔系统提示和用户模板"
          style="width: 1100px"
        />
      </el-form-item>

      <el-divider content-position="left">分析数据源</el-divider>

      <el-form-item label="包含 RSS 内容">
        <el-switch v-model="form.include_rss" />
      </el-form-item>

      <el-form-item label="包含独立展示区">
        <el-switch v-model="form.include_standalone" />
      </el-form-item>

      <el-form-item label="传递完整排名时间线">
        <el-switch v-model="form.include_rank_timeline" />
        <span style="color: #909399; font-size: 12px; margin-left: 8px">传递完整的排名变化历史给 AI</span>
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
  enabled: false,
  language: '中文',
  mode: 'follow_report',
  max_news_for_analysis: 50,
  prompt_content: '',
  include_rss: true,
  include_standalone: false,
  include_rank_timeline: false,
})

let originalConfig = null

onMounted(async () => {
  await loadConfig()
})

async function loadConfig() {
  const config = await configApi.getFullConfig()
  const ai = config.ai_analysis || {}
  Object.assign(form, {
    enabled: ai.enabled || false,
    language: ai.language || '中文',
    mode: ai.mode || 'follow_report',
    max_news_for_analysis: ai.max_news_for_analysis || 50,
    prompt_content: ai.prompt_content || '',
    include_rss: ai.include_rss !== false,
    include_standalone: ai.include_standalone || false,
    include_rank_timeline: ai.include_rank_timeline || false,
  })
  originalConfig = { ...form }
}

async function save() {
  saving.value = true
  try {
    const config = await configApi.getFullConfig()
    config.ai_analysis = { ...form }
    await configApi.updateFullConfig(config)
    ElMessage.success('AI 分析配置已保存')
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
