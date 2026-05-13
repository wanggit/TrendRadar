<template>
  <div class="tasks-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>任务调度</span>
          <div class="actions">
            <el-button type="primary" @click="triggerCrawl" :loading="loading.crawl">触发爬虫</el-button>
            <el-button type="success" @click="triggerAnalyze" :loading="loading.analyze">触发分析</el-button>
            <el-button type="warning" @click="triggerPush" :loading="loading.push">触发推送</el-button>
          </div>
        </div>
      </template>
      
      <el-descriptions :column="2" border>
        <el-descriptions-item label="调度状态">
          <el-tag :type="schedule.enabled ? 'success' : 'danger'">
            {{ schedule.enabled ? '运行中' : '已停止' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="预设模板">{{ schedule.preset }}</el-descriptions-item>
        <el-descriptions-item label="定时任务数">{{ schedule.entries.length }}</el-descriptions-item>
        <el-descriptions-item label="任务列表">
          <el-tag v-for="entry in schedule.entries" :key="entry" size="small" style="margin: 2px">
            {{ entry }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
      
      <div style="margin-top: 20px">
        <h4>任务说明</h4>
        <el-alert title="爬虫任务" description="从各热榜平台和 RSS 源抓取最新数据" type="info" :closable="false" style="margin-bottom: 10px" />
        <el-alert title="AI 分析任务" description="使用 AI 对抓取的数据进行智能筛选和深度分析" type="success" :closable="false" style="margin-bottom: 10px" />
        <el-alert title="推送任务" description="将分析结果推送到配置的通知渠道（飞书、钉钉、Telegram 等）" type="warning" :closable="false" />
      </div>
    </el-card>

    <el-card style="margin-top: 20px" v-if="runningTasks.length > 0">
      <template #header>
        <div class="card-header">
          <span>正在执行的任务</span>
          <el-badge :value="runningTasks.length" type="primary" />
        </div>
      </template>
      <div class="running-tasks">
        <div v-for="task in runningTasks" :key="task.task_id" class="running-task-item">
          <div class="task-info">
            <div class="task-name">
              <el-icon class="task-icon spinning"><Loading /></el-icon>
              {{ getTaskDisplayName(task.task_name) }}
            </div>
            <div class="task-step">{{ task.current_step || '准备中...' }}</div>
          </div>
          <div class="task-progress">
            <el-progress :percentage="task.progress" :status="task.progress === 100 ? 'success' : ''" :stroke-width="8" />
          </div>
          <div class="task-meta">
            <span class="task-elapsed">已运行 {{ formatElapsed(task.elapsed_seconds) }}</span>
            <el-tag size="small" :type="getStatusType(task.status)">{{ getStatusText(task.status) }}</el-tag>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { taskApi } from '@/api/task'
import { ElMessage } from 'element-plus'

const loading = reactive({
  crawl: false,
  analyze: false,
  push: false,
})

const schedule = reactive({
  enabled: false,
  preset: '',
  entries: [],
})

const runningTasks = ref([])
let pollingTimer = null

const taskNames = {
  crawl_platforms: '平台抓取',
  crawl_rss: 'RSS 抓取',
  analyze_news: 'AI 分析',
  push_notification: '推送通知',
}

const statusTypes = {
  pending: 'info',
  running: 'warning',
  started: 'warning',
  success: 'success',
  failure: 'danger',
  error: 'danger',
}

const statusTexts = {
  pending: '等待中',
  running: '运行中',
  started: '运行中',
  success: '已完成',
  failure: '失败',
  error: '错误',
}

function getTaskDisplayName(name) {
  return taskNames[name] || name
}

function getStatusType(status) {
  return statusTypes[status] || 'info'
}

function getStatusText(status) {
  return statusTexts[status] || status
}

function formatElapsed(seconds) {
  if (!seconds) return '0秒'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  if (mins > 0) return `${mins}分${secs}秒`
  return `${secs}秒`
}

async function fetchRunningTasks() {
  try {
    const tasks = await taskApi.getRunningTasks()
    runningTasks.value = tasks
  } catch (e) {
    // Silently fail
  }
}

function startPolling() {
  fetchRunningTasks()
  pollingTimer = setInterval(fetchRunningTasks, 3000)
}

function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

onMounted(async () => {
  const data = await taskApi.getSchedule()
  Object.assign(schedule, data)
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})

async function triggerCrawl() {
  loading.crawl = true
  try {
    const res = await taskApi.triggerCrawl({})
    ElMessage.success(`爬虫任务已触发 (${res.tasks?.length || 0} 个子任务)`)
    setTimeout(fetchRunningTasks, 1000)
  } finally {
    loading.crawl = false
  }
}

async function triggerAnalyze() {
  loading.analyze = true
  try {
    await taskApi.triggerAnalyze()
    ElMessage.success('AI 分析任务已触发')
    setTimeout(fetchRunningTasks, 1000)
  } finally {
    loading.analyze = false
  }
}

async function triggerPush() {
  loading.push = true
  try {
    await taskApi.triggerPush()
    ElMessage.success('推送任务已触发')
    setTimeout(fetchRunningTasks, 1000)
  } finally {
    loading.push = false
  }
}
</script>

<style scoped>
.tasks-page {
  padding: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.actions {
  display: flex;
  gap: 10px;
}

.running-tasks {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.running-task-item {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #409eff;
}

.task-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.task-name {
  font-weight: 600;
  font-size: 15px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-icon {
  color: #409eff;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.task-step {
  color: #606266;
  font-size: 13px;
}

.task-progress {
  margin-bottom: 6px;
}

.task-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-elapsed {
  color: #909399;
  font-size: 12px;
}
</style>
