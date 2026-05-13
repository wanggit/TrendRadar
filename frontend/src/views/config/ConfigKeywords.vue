<template>
  <div>
    <div class="module-header">
      <h3>关注关键词</h3>
      <el-button type="primary" @click="save" :loading="saving">保存</el-button>
    </div>

    <el-alert
      title="每行一个关键词或词组。支持正则表达式（用 /包裹）和别名语法（=>）。"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    />

    <div class="keyword-hints">
      <el-tag size="small" type="info">普通关键词</el-tag>
      <el-tag size="small" type="success">正则: /AI|人工智能/</el-tag>
      <el-tag size="small" type="warning">别名: 胖东来 => 胖东来集团</el-tag>
      <el-tag size="small" type="danger">排除: !广告</el-tag>
      <el-tag size="small">必须: +必须词</el-tag>
    </div>

    <el-input
      v-model="keywords"
      type="textarea"
      :rows="20"
      placeholder="每行一个关键词或词组...&#10;&#10;示例:&#10;人工智能&#10;/AI|大模型/&#10;胖东来 => 胖东来集团&#10;!广告&#10;+必须词"
      class="keyword-editor"
    />

    <div class="word-count">
      共 {{ keywordLines.length }} 个关键词/词组
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { configApi } from '@/api/config'
import { ElMessage } from 'element-plus'

const saving = ref(false)
const keywords = ref('')

const keywordLines = computed(() => {
  return keywords.value.split('\n').filter(line => line.trim())
})

onMounted(async () => {
  await loadKeywords()
})

async function loadKeywords() {
  const data = await configApi.getFrequencyWords()
  keywords.value = data.frequency_words || ''
}

async function save() {
  saving.value = true
  try {
    await configApi.updateFrequencyWords({ frequency_words: keywords.value })
    ElMessage.success('关键词已保存')
  } finally {
    saving.value = false
  }
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

.keyword-hints {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.keyword-editor {
  font-family: 'Courier New', monospace;
}

.word-count {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}
</style>
