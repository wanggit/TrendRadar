import api from './index'

export const taskApi = {
  triggerCrawl(data) {
    return api.post('/tasks/trigger/crawl', data)
  },
  triggerAnalyze() {
    return api.post('/tasks/trigger/analyze')
  },
  triggerPush() {
    return api.post('/tasks/trigger/push')
  },
  getTaskStatus(taskId) {
    return api.get(`/tasks/status/${taskId}`)
  },
  getSchedule() {
    return api.get('/tasks/schedule')
  },
  getRunningTasks() {
    return api.get('/tasks/running')
  },
  getTaskLogs(params = {}) {
    return api.get('/tasks/logs', { params })
  },
  getTaskLog(taskId) {
    return api.get(`/tasks/logs/${taskId}`)
  },
  deleteTaskLog(taskId) {
    return api.delete(`/tasks/logs/${taskId}`)
  },
  getLatestReport() {
    return api.get('/tasks/reports/latest')
  },
  getReport(reportId) {
    return api.get(`/tasks/reports/${reportId}`)
  },
  getReports(params = {}) {
    return api.get('/tasks/reports', { params })
  },
}
