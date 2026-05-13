<template>
  <div>
    <div class="module-header">
      <h3>AI 智能筛选</h3>
    </div>

    <el-alert
      title="仅当筛选策略选择 AI 模式时生效"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    />

    <el-form :model="form" label-width="180px" style="max-width: 1100px">
      <el-form-item label="每批标题数量">
        <el-input-number v-model="form.batch_size" :min="1" :max="200" style="width: 120px" />
        <span style="color: #909399; font-size: 12px; margin-left: 8px">每次发送给 AI 的标题数量</span>
      </el-form-item>

      <el-form-item label="分批间隔 (秒)">
        <el-input-number v-model="form.batch_interval" :min="0" :max="300" style="width: 120px" />
        <span style="color: #909399; font-size: 12px; margin-left: 8px">批次之间的等待时间，避免 API 限流</span>
      </el-form-item>

      <el-form-item label="最低分数阈值">
        <el-input-number v-model="form.min_score" :min="0" :max="1" :step="0.1" :precision="1" style="width: 120px" />
        <span style="color: #909399; font-size: 12px; margin-left: 8px">0~1，低于此分数的条目将被过滤</span>
      </el-form-item>

      <el-form-item label="全量重分类阈值">
        <el-input-number v-model="form.reclassify_threshold" :min="0" :max="1" :step="0.1" :precision="1" style="width: 120px" />
        <span style="color: #909399; font-size: 12px; margin-left: 8px">低于此分数时触发全量标签重分类</span>
      </el-form-item>

      <el-form-item label="兴趣描述">
        <el-input
          v-model="form.interests_content"
          type="textarea"
          :rows="10"
          placeholder="用自然语言描述你关注的话题，AI 会自动提取标签并对新闻进行分类"
          style="width: 100%"
        />
        <div style="color: #909399; font-size: 12px; margin-top: 4px">
          描述你关注的新闻方向，越具体越好。支持使用 # 注释。
        </div>
      </el-form-item>

      <el-form-item label="分类提示词">
        <el-input
          v-model="form.classify_prompt"
          type="textarea"
          :rows="12"
          placeholder="分类提示词模板，支持 [system] 和 [user] 分段"
          style="width: 100%"
        />
        <div style="color: #909399; font-size: 12px; margin-top: 4px">
          用于对新闻标题进行分类的提示词。支持 {interests_content}、{tags_list}、{news_count}、{news_list} 占位符。
        </div>
      </el-form-item>

      <el-form-item label="标签提取提示词">
        <el-input
          v-model="form.extract_prompt"
          type="textarea"
          :rows="10"
          placeholder="标签提取提示词模板，支持 [system] 和 [user] 分段"
          style="width: 100%"
        />
        <div style="color: #909399; font-size: 12px; margin-top: 4px">
          用于从兴趣描述中提取结构化标签的提示词。支持 {interests_content} 占位符。
        </div>
      </el-form-item>

      <el-form-item label="标签更新提示词">
        <el-input
          v-model="form.update_tags_prompt"
          type="textarea"
          :rows="12"
          placeholder="标签更新提示词模板，支持 [system] 和 [user] 分段"
          style="width: 100%"
        />
        <div style="color: #909399; font-size: 12px; margin-top: 4px">
          用于对比旧标签和新兴趣描述，给出标签更新方案的提示词。支持 {old_tags_json}、{interests_content} 占位符。
        </div>
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
  batch_size: 200,
  batch_interval: 2,
  min_score: 0.7,
  reclassify_threshold: 0.6,
  interests_content: '',
  classify_prompt: '',
  extract_prompt: '',
  update_tags_prompt: '',
})

let originalConfig = null

onMounted(async () => {
  await loadConfig()
})

async function loadConfig() {
  const config = await configApi.getFullConfig()
  const ai = config.ai_filter || {}
  Object.assign(form, {
    batch_size: ai.batch_size || 200,
    batch_interval: ai.batch_interval || 2,
    min_score: ai.min_score || 0.7,
    reclassify_threshold: ai.reclassify_threshold || 0.6,
    interests_content: ai.interests_content || '',
    classify_prompt: ai.classify_prompt || '',
    extract_prompt: ai.extract_prompt || '',
    update_tags_prompt: ai.update_tags_prompt || '',
  })
  originalConfig = { ...form }
}

async function save() {
  saving.value = true
  try {
    const config = await configApi.getFullConfig()
    config.ai_filter = { ...form }
    await configApi.updateFullConfig(config)
    ElMessage.success('AI 智能筛选配置已保存')
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
