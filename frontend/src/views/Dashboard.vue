<template>
  <div class="dashboard">
    <el-alert
      v-if="authStore.isTrialActive"
      :title="`免费试用剩余 ${authStore.trialDaysLeft} 天`"
      :type="authStore.isTrialExpiringSoon ? 'warning' : 'success'"
      :closable="false"
      show-icon
      class="trial-banner"
    >
      <template #default>
        <span v-if="authStore.isTrialExpiringSoon">试用即将结束，</span>
        <el-button size="small" type="primary" @click="$router.push('/purchase')">
          立即购买专业版
        </el-button>
      </template>
    </el-alert>

    <el-alert
      v-if="authStore.isTrialExpired"
      title="试用已结束，请购买专业版继续使用完整功能"
      type="error"
      :closable="false"
      show-icon
      class="trial-banner"
    >
      <template #default>
        <el-button size="small" type="primary" @click="$router.push('/purchase')">
          购买专业版
        </el-button>
      </template>
    </el-alert>

    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>热榜平台</span>
              <el-icon><Monitor /></el-icon>
            </div>
          </template>
          <div class="stat-value">{{ stats.platforms }}</div>
          <div class="stat-label">已启用</div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>RSS 订阅</span>
              <el-icon><Rss /></el-icon>
            </div>
          </template>
          <div class="stat-value">{{ stats.rss }}</div>
          <div class="stat-label">已启用</div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>今日新闻</span>
              <el-icon><Document /></el-icon>
            </div>
          </template>
          <div class="stat-value">{{ stats.news }}</div>
          <div class="stat-label">已抓取</div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>调度状态</span>
              <el-icon><Timer /></el-icon>
            </div>
          </template>
          <div class="stat-value">{{ schedule.preset }}</div>
          <div class="stat-label">{{ schedule.enabled ? '运行中' : '已停止' }}</div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>快捷操作</span>
            </div>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="triggerCrawl" :loading="loading.crawl">
              <el-icon><Download /></el-icon>
              手动抓取
            </el-button>
            <el-button type="success" @click="triggerAnalyze" :loading="loading.analyze">
              <el-icon><Cpu /></el-icon>
              AI 分析
            </el-button>
            <el-button type="warning" @click="triggerPush" :loading="loading.push">
              <el-icon><Bell /></el-icon>
              立即推送
            </el-button>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>系统 AI 配置</span>
              <el-tag size="small" type="info">只读</el-tag>
            </div>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="模型">{{ aiConfig.model }}</el-descriptions-item>
            <el-descriptions-item label="API 地址">{{ aiConfig.api_base }}</el-descriptions-item>
            <el-descriptions-item label="Temperature">{{ aiConfig.temperature }}</el-descriptions-item>
            <el-descriptions-item label="Max Tokens">{{ aiConfig.max_tokens }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px" v-if="runningTasks.length > 0">
      <el-col :span="24">
        <el-card>
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
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px" v-if="latestReport">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>AI 分析报告</span>
              <div class="report-header-actions">
                <span class="report-time">{{ formatReportTime(latestReport.created_at) }}</span>
                <el-button size="small" @click="refreshReport" :loading="reportLoading">
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
              </div>
            </div>
          </template>

          <div v-if="!latestReport.success" class="report-error">
            <el-alert type="error" :title="latestReport.error || '分析失败'" :closable="false" show-icon />
          </div>

          <div v-else class="report-content">
            <el-descriptions :column="3" border class="report-stats" size="small">
              <el-descriptions-item label="分析新闻">{{ latestReport.analyzed_news }} 条</el-descriptions-item>
              <el-descriptions-item label="热榜">{{ latestReport.hotlist_count }} 条</el-descriptions-item>
              <el-descriptions-item label="RSS">{{ latestReport.rss_count }} 条</el-descriptions-item>
            </el-descriptions>

            <el-tabs type="border-card" class="report-tabs">
              <el-tab-pane label="核心热点态势">
                <div class="report-section" v-html="formatReportText(latestReport.core_trends)"></div>
              </el-tab-pane>
              <el-tab-pane label="舆论风向争议">
                <div class="report-section" v-html="formatReportText(latestReport.sentiment_controversy)"></div>
              </el-tab-pane>
              <el-tab-pane label="异动与弱信号">
                <div class="report-section" v-html="formatReportText(latestReport.signals)"></div>
              </el-tab-pane>
              <el-tab-pane label="RSS深度洞察" v-if="latestReport.rss_insights && latestReport.rss_insights !== '未开启RSS分析'">
                <div class="report-section" v-html="formatReportText(latestReport.rss_insights)"></div>
              </el-tab-pane>
              <el-tab-pane label="研判策略建议">
                <div class="report-section" v-html="formatReportText(latestReport.outlook_strategy)"></div>
              </el-tab-pane>
              <el-tab-pane v-if="latestReport.standalone_summaries && Object.keys(latestReport.standalone_summaries).length > 0" label="独立展示区概括">
                <div v-for="(summary, source) in latestReport.standalone_summaries" :key="source" class="standalone-item">
                  <h4>{{ source }}</h4>
                  <p v-html="formatReportText(summary)"></p>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { configApi } from '@/api/config'
import { dataApi } from '@/api/data'
import { taskApi } from '@/api/task'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const authStore = useAuthStore()

const stats = reactive({
  platforms: 0,
  rss: 0,
  news: 0,
})

const schedule = reactive({
  enabled: false,
  preset: '',
})

const aiConfig = reactive({
  model: '',
  api_base: '',
  temperature: 0,
  max_tokens: 0,
})

const loading = reactive({
  crawl: false,
  analyze: false,
  push: false,
})

const runningTasks = ref([])
let pollingTimer = null

const latestReport = ref(null)
const reportLoading = ref(false)

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

    const hasAnalyzeRunning = tasks.some(t => t.task_name === 'analyze_news' && (t.status === 'running' || t.status === 'pending'))
    if (!hasAnalyzeRunning && !reportLoading.value) {
      await fetchLatestReport()
    }
  } catch (e) {
    // Silently fail
  }
}

async function fetchLatestReport() {
  try {
    const report = await taskApi.getLatestReport()
    if (report) {
      latestReport.value = report
    }
  } catch (e) {
    // Silently fail
  }
}

async function refreshReport() {
  reportLoading.value = true
  try {
    await fetchLatestReport()
  } catch (e) {
    ElMessage.error('刷新报告失败')
  } finally {
    reportLoading.value = false
  }
}

function formatReportTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatReportText(text) {
  if (!text) return ''
  return text
    .replace(/\n/g, '<br>')
    .replace(/【([^】]+)】/g, '<strong>【$1】</strong>')
    .replace(/「([^」]+)」/g, '<em>「$1」</em>')
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
  try {
    const [platforms, rssFeeds, news, sched, ai] = await Promise.all([
      dataApi.getPlatforms(),
      dataApi.getRssFeeds(),
      dataApi.getNews({ limit: 1 }),
      configApi.getSchedule(),
      configApi.getSystemAIConfig(),
    ])
    
    stats.platforms = platforms.filter(p => p.enabled).length
    stats.rss = rssFeeds.filter(f => f.enabled !== false).length
    stats.news = news.total || 0
    schedule.enabled = sched.enabled
    schedule.preset = sched.preset
    Object.assign(aiConfig, ai)
  } catch (e) {
    ElMessage.error('加载仪表盘数据失败')
  }

  await fetchLatestReport()
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
  } catch (e) {
    // Error handled by interceptor
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
  } catch (e) {
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
  } catch (e) {
  } finally {
    loading.push = false
  }
}
</script>

<style scoped>
.dashboard {
  padding: 10px;
}

.trial-banner {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #409eff;
  text-align: center;
  margin: 10px 0;
}

.stat-label {
  text-align: center;
  color: #909399;
  font-size: 14px;
}

.quick-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
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

.report-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.report-time {
  color: #909399;
  font-size: 13px;
}

.report-error {
  padding: 10px 0;
}

.report-stats {
  margin-bottom: 16px;
}

.report-tabs {
  margin-top: 12px;
}

.report-section {
  padding: 16px;
  line-height: 1.8;
  font-size: 14px;
  color: #303133;
  white-space: pre-wrap;
  word-break: break-word;
}

.report-section strong {
  color: #409eff;
  font-weight: 600;
}

.report-section em {
  color: #e6a23c;
  font-style: normal;
  font-weight: 500;
}

.standalone-item {
  padding: 12px 0;
  border-bottom: 1px solid #ebeef5;
}

.standalone-item:last-child {
  border-bottom: none;
}

.standalone-item h4 {
  margin: 0 0 8px 0;
  color: #409eff;
  font-size: 15px;
}

.standalone-item p {
  margin: 0;
  line-height: 1.8;
  color: #606266;
}
</style>
