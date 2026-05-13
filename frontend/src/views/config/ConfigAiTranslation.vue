<template>
  <div>
    <div class="module-header">
      <h3>AI 翻译功能</h3>
    </div>

    <el-alert
      title="AI 翻译功能自动将非中文内容翻译为目标语言"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    />

    <el-form :model="form" label-width="140px" style="max-width: 600px">
      <el-form-item label="开启 AI 翻译">
        <el-switch v-model="form.enabled" />
      </el-form-item>

      <el-form-item label="目标语言">
        <el-input v-model="form.language" placeholder="例如: 中文" style="width: 200px" />
      </el-form-item>

      <el-form-item label="提示词文件">
        <el-input v-model="form.prompt_file" placeholder="例如: translation_prompt.txt" style="width: 300px" />
      </el-form-item>

      <el-divider content-position="left">翻译范围</el-divider>

      <el-form-item label="热榜内容">
        <el-switch v-model="form.scope.hotlist" />
      </el-form-item>

      <el-form-item label="RSS 内容">
        <el-switch v-model="form.scope.rss" />
      </el-form-item>

      <el-form-item label="独立展示区">
        <el-switch v-model="form.scope.standalone" />
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
  prompt_file: 'translation_prompt.txt',
  scope: {
    hotlist: true,
    rss: true,
    standalone: false,
  },
})

let originalConfig = null

onMounted(async () => {
  await loadConfig()
})

async function loadConfig() {
  const config = await configApi.getFullConfig()
  const ai = config.ai_translation || {}
  Object.assign(form, {
    enabled: ai.enabled || false,
    language: ai.language || '中文',
    prompt_file: ai.prompt_file || 'translation_prompt.txt',
    scope: {
      hotlist: ai.scope?.hotlist !== false,
      rss: ai.scope?.rss !== false,
      standalone: ai.scope?.standalone || false,
    },
  })
  originalConfig = JSON.parse(JSON.stringify(form))
}

async function save() {
  saving.value = true
  try {
    const config = await configApi.getFullConfig()
    config.ai_translation = { ...form }
    await configApi.updateFullConfig(config)
    ElMessage.success('AI 翻译配置已保存')
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
