<template>
  <div class="task-history">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>任务执行历史</span>
          <div class="actions">
            <el-button :icon="Refresh" @click="refresh" :loading="loading">刷新</el-button>
          </div>
        </div>
      </template>

      <div class="filters">
        <el-select v-model="filterTaskName" placeholder="任务类型" clearable style="width: 160px" @change="applyFilters">
          <el-option label="全部" value="" />
          <el-option label="平台抓取" value="crawl_platforms" />
          <el-option label="RSS 抓取" value="crawl_rss" />
          <el-option label="AI 分析" value="analyze_news" />
          <el-option label="推送通知" value="push_notification" />
        </el-select>
        <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 120px" @change="applyFilters">
          <el-option label="全部" value="" />
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failure" />
          <el-option label="运行中" value="running" />
          <el-option label="等待中" value="pending" />
        </el-select>
      </div>

      <el-table :data="taskLogs" style="width: 100%" v-loading="loading" stripe>
        <el-table-column prop="task_name" label="任务" width="140">
          <template #default="{ row }">
            {{ getTaskDisplayName(row.task_name) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="140">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :status="row.status === 'success' ? 'success' : (row.status === 'failure' ? 'exception' : '')" :stroke-width="6" />
          </template>
        </el-table-column>
        <el-table-column prop="current_step" label="当前步骤" min-width="180">
          <template #default="{ row }">
            {{ row.current_step || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="duration_seconds" label="耗时" width="100">
          <template #default="{ row }">
            {{ formatDuration(row.duration_seconds) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="开始时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="showLogDetail(row)">详情</el-button>
            <el-button
              v-if="['pending', 'failure', 'error'].includes(row.status)"
              link
              type="danger"
              @click="deleteTask(row)"
              :loading="row._deleting"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchLogs"
          @current-change="fetchLogs"
        />
      </div>
    </el-card>

    <el-dialog v-model="logDetailVisible" title="任务执行日志" width="700px">
      <div v-if="selectedLog" class="log-detail">
        <el-descriptions :column="2" border class="log-meta">
          <el-descriptions-item label="任务">{{ getTaskDisplayName(selectedLog.task_name) }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedLog.status)">{{ getStatusText(selectedLog.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ formatTime(selectedLog.started_at || selectedLog.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ selectedLog.completed_at ? formatTime(selectedLog.completed_at) : '-' }}</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ formatDuration(selectedLog.duration_seconds) }}</el-descriptions-item>
          <el-descriptions-item label="进度">{{ selectedLog.progress }}%</el-descriptions-item>
        </el-descriptions>

        <div class="log-section">
          <h4>执行日志</h4>
          <div class="log-entries">
            <div v-for="(entry, idx) in selectedLog.logs" :key="idx" :class="['log-entry', `log-${entry.level}`]">
              <span class="log-time">{{ formatLogTime(entry.timestamp) }}</span>
              <el-tag :type="getLogLevelType(entry.level)" size="small" class="log-level">{{ entry.level.toUpperCase() }}</el-tag>
              <span class="log-message">{{ entry.message }}</span>
            </div>
            <div v-if="!selectedLog.logs || selectedLog.logs.length === 0" class="no-logs">
              暂无日志记录
            </div>
          </div>
        </div>

        <div v-if="selectedLog.error_message" class="error-section">
          <h4>错误信息</h4>
          <el-alert :title="selectedLog.error_message" type="error" :closable="false" show-icon />
        </div>

        <div v-if="selectedLog.result" class="result-section">
          <h4>执行结果</h4>
          <pre class="result-json">{{ JSON.stringify(selectedLog.result, null, 2) }}</pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { taskApi } from '@/api/task'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'

const taskLogs = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filterTaskName = ref('')
const filterStatus = ref('')
const logDetailVisible = ref(false)
const selectedLog = ref(null)

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
  success: '成功',
  failure: '失败',
  error: '错误',
}

const logLevelTypes = {
  info: 'info',
  success: 'success',
  warning: 'warning',
  error: 'danger',
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

function getLogLevelType(level) {
  return logLevelTypes[level] || 'info'
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return '-'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  if (mins > 0) return `${mins}分${secs}秒`
  return `${secs.toFixed(1)}秒`
}

function formatTime(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', { hour12: false })
}

function formatLogTime(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

async function fetchLogs() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (filterTaskName.value) params.task_name = filterTaskName.value
    if (filterStatus.value) params.status = filterStatus.value

    const res = await taskApi.getTaskLogs(params)
    taskLogs.value = res.logs
    total.value = res.total
  } catch (e) {
    ElMessage.error('加载任务历史失败')
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  currentPage.value = 1
  fetchLogs()
}

function refresh() {
  fetchLogs()
}

function showLogDetail(log) {
  selectedLog.value = log
  logDetailVisible.value = true
}

async function deleteTask(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除任务「${getTaskDisplayName(row.task_name)}」吗？`,
      '删除任务',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    row._deleting = true
    await taskApi.deleteTaskLog(row.task_id)
    ElMessage.success('任务已删除')
    fetchLogs()
  } catch (e) {
    if (e !== 'cancel') {
      const msg = e.response?.data?.detail || '删除失败'
      ElMessage.error(msg)
    }
  } finally {
    row._deleting = false
  }
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.task-history {
  padding: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.log-detail {
  max-height: 60vh;
  overflow-y: auto;
}

.log-meta {
  margin-bottom: 20px;
}

.log-section,
.error-section,
.result-section {
  margin-top: 20px;
}

.log-section h4,
.error-section h4,
.result-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #303133;
}

.log-entries {
  background: #1e1e1e;
  border-radius: 6px;
  padding: 12px;
  max-height: 300px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.log-entry {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 4px 0;
  line-height: 1.5;
}

.log-time {
  color: #888;
  white-space: nowrap;
  min-width: 80px;
}

.log-level {
  min-width: 50px;
  text-align: center;
}

.log-message {
  color: #e0e0e0;
  flex: 1;
}

.log-info .log-message {
  color: #e0e0e0;
}

.log-success .log-message {
  color: #67c23a;
}

.log-warning .log-message {
  color: #e6a23c;
}

.log-error .log-message {
  color: #f56c6c;
}

.no-logs {
  color: #666;
  text-align: center;
  padding: 20px;
}

.result-json {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  max-height: 200px;
  overflow: auto;
}
</style>
