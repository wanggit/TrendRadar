<template>
  <div class="config-page">
    <div class="config-layout">
      <div class="config-sidebar">
        <div class="sidebar-title">配置中心</div>
        <nav class="sidebar-nav">
          <div
            v-for="mod in modules"
            :key="mod.key"
            class="nav-item"
            :class="{ active: activeModule === mod.key }"
            @click="activeModule = mod.key"
          >
            <el-icon><component :is="mod.icon" /></el-icon>
            <span>{{ mod.label }}</span>
          </div>
        </nav>
        <div class="sidebar-footer">
          <el-button size="small" text @click="showDiffDialog = true">
            <el-icon><Rank /></el-icon> 版本对比
          </el-button>
          <el-button size="small" text @click="exportConfig">
            <el-icon><Download /></el-icon> 导出配置
          </el-button>
          <el-button size="small" text @click="triggerImport">
            <el-icon><Upload /></el-icon> 导入配置
          </el-button>
          <input ref="importInput" type="file" accept=".json" style="display: none" @change="importConfig" />
        </div>
      </div>

      <div class="config-content">
        <component :is="currentComponent" />
      </div>
    </div>

    <!-- Config Diff Dialog -->
    <el-dialog v-model="showDiffDialog" title="配置版本对比" width="700px">
      <div v-if="diffData" class="diff-container">
        <div v-if="Object.keys(diffData.modified).length === 0" class="diff-empty">
          <el-icon><CircleCheck /></el-icon>
          <p>所有配置均为默认值</p>
        </div>
        <div v-else>
          <div class="diff-summary">
            已修改 <strong>{{ Object.keys(diffData.modified).length }}</strong> 项配置
          </div>
          <div v-for="(values, key) in diffData.modified" :key="key" class="diff-item">
            <div class="diff-key">{{ diffLabels[key] || key }}</div>
            <div class="diff-values">
              <div class="diff-current">
                <span class="diff-label">当前</span>
                <pre>{{ formatDiffValue(values.current) }}</pre>
              </div>
              <div class="diff-default">
                <span class="diff-label">默认</span>
                <pre>{{ formatDiffValue(values.default) }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showDiffDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Setting, List, Connection, Document, Filter, Monitor, Bell, DataAnalysis, Clock, ChatLineRound, Tools, Download, Upload, Rank, CircleCheck } from '@element-plus/icons-vue'
import { configApi } from '@/api/config'
import { ElMessage } from 'element-plus'

import ConfigPlatforms from './config/ConfigPlatforms.vue'
import ConfigReport from './config/ConfigReport.vue'
import ConfigFilter from './config/ConfigFilter.vue'
import ConfigAiFilter from './config/ConfigAiFilter.vue'
import ConfigDisplay from './config/ConfigDisplay.vue'
import ConfigNotification from './config/ConfigNotification.vue'
import ConfigRss from './config/ConfigRss.vue'
import ConfigSchedule from './config/ConfigSchedule.vue'
import ConfigTimeline from './config/ConfigTimeline.vue'
import ConfigKeywords from './config/ConfigKeywords.vue'
import ConfigAiAnalysis from './config/ConfigAiAnalysis.vue'
import ConfigAiTranslation from './config/ConfigAiTranslation.vue'
import ConfigAdvanced from './config/ConfigAdvanced.vue'

const modules = [
  { key: 'platforms',    label: '热榜平台',   icon: List,              component: ConfigPlatforms },
  { key: 'rss',          label: 'RSS 订阅',   icon: Connection,          component: ConfigRss },
  { key: 'report',       label: '报告模式',   icon: Document,          component: ConfigReport },
  { key: 'filter',       label: '筛选策略',   icon: Filter,            component: ConfigFilter },
  { key: 'ai_filter',    label: 'AI 智能筛选', icon: DataAnalysis,      component: ConfigAiFilter },
  { key: 'display',      label: '推送内容控制', icon: Monitor,          component: ConfigDisplay },
  { key: 'notification', label: '推送通知',   icon: Bell,              component: ConfigNotification },
  { key: 'schedule',     label: '调度设置',   icon: Clock,             component: ConfigSchedule },
  { key: 'timeline',     label: '调度时间线', icon: Clock,             component: ConfigTimeline },
  { key: 'keywords',     label: '关键词',     icon: Setting,           component: ConfigKeywords },
  { key: 'ai_analysis',  label: 'AI 分析',    icon: DataAnalysis,      component: ConfigAiAnalysis },
  { key: 'ai_translation', label: 'AI 翻译',  icon: ChatLineRound,     component: ConfigAiTranslation },
  { key: 'advanced',     label: '高级设置',   icon: Tools,             component: ConfigAdvanced },
]

const activeModule = ref('platforms')
const showDiffDialog = ref(false)
const diffData = ref(null)
const importInput = ref(null)

const diffLabels = {
  timezone: '时区',
  platforms: '热榜平台',
  rss: 'RSS 订阅',
  report: '报告模式',
  filter_strategy: '筛选策略',
  ai_filter: 'AI 智能筛选',
  display: '推送内容控制',
  notification: '推送通知',
  schedule: '调度设置',
  timeline: '调度时间线',
  frequency_words: '关键词',
  ai_analysis: 'AI 分析',
  ai_translation: 'AI 翻译',
  storage: '存储配置',
  advanced: '高级设置',
}

const currentComponent = computed(() => {
  const mod = modules.find(m => m.key === activeModule.value)
  return mod ? mod.component : ConfigPlatforms
})

onMounted(() => {
  loadDiff()
})

async function loadDiff() {
  try {
    diffData.value = await configApi.getConfigDiff()
  } catch {
    diffData.value = null
  }
}

async function exportConfig() {
  try {
    const config = await configApi.getFullConfig()
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `trendradar-config-${new Date().toISOString().split('T')[0]}.json`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('配置已导出')
  } catch {
    ElMessage.error('导出失败')
  }
}

function triggerImport() {
  importInput.value?.click()
}

async function importConfig(event) {
  const file = event.target.files?.[0]
  if (!file) return

  try {
    const formData = new FormData()
    formData.append('file', file)
    await configApi.importConfig(formData)
    ElMessage.success('配置已导入')
    await loadDiff()
  } catch {
    ElMessage.error('导入失败，请检查文件格式')
  }

  event.target.value = ''
}

function formatDiffValue(value) {
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2)
  }
  return String(value)
}
</script>

<style scoped>
.config-page {
  height: calc(100vh - 120px);
}

.config-layout {
  display: flex;
  height: 100%;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}

.config-sidebar {
  width: 200px;
  background: #fafbfc;
  border-right: 1px solid #e4e7ed;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.sidebar-title {
  padding: 16px 20px;
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  border-bottom: 1px solid #e4e7ed;
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  cursor: pointer;
  color: #606266;
  font-size: 13px;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: #ecf5ff;
  color: #409eff;
}

.nav-item.active {
  background: #ecf5ff;
  color: #409eff;
  border-left-color: #409eff;
  font-weight: 500;
}

.nav-item .el-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.sidebar-footer {
  padding: 8px 12px;
  border-top: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar-footer .el-button {
  justify-content: flex-start;
  color: #909399;
}

.sidebar-footer .el-button:hover {
  color: #409eff;
}

.config-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.diff-container {
  max-height: 500px;
  overflow-y: auto;
}

.diff-empty {
  text-align: center;
  padding: 40px;
  color: #909399;
}

.diff-empty .el-icon {
  font-size: 48px;
  color: #67c23a;
  margin-bottom: 12px;
}

.diff-summary {
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 6px;
  margin-bottom: 12px;
  font-size: 13px;
}

.diff-item {
  margin-bottom: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow: hidden;
}

.diff-key {
  padding: 8px 12px;
  background: #fafbfc;
  font-weight: 600;
  font-size: 13px;
  color: #303133;
  border-bottom: 1px solid #e4e7ed;
}

.diff-values {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
}

.diff-current, .diff-default {
  padding: 8px 12px;
}

.diff-current {
  border-right: 1px solid #e4e7ed;
}

.diff-label {
  display: block;
  font-size: 11px;
  color: #909399;
  margin-bottom: 4px;
}

.diff-current pre, .diff-default pre {
  margin: 0;
  font-size: 12px;
  font-family: monospace;
  white-space: pre-wrap;
  word-break: break-all;
  color: #606266;
}
</style>
