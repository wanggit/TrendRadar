import api from './index'

export const configApi = {
  getFullConfig() {
    return api.get('/config/')
  },
  updateFullConfig(data) {
    return api.put('/config/', data)
  },
  getRuntimeConfig() {
    return api.get('/config/runtime')
  },
  getSystemAIConfig() {
    return api.get('/config/ai-system')
  },
  getPlatforms() {
    return api.get('/config/platforms')
  },
  updatePlatforms(data) {
    return api.put('/config/platforms', data)
  },
  getSchedule() {
    return api.get('/config/schedule')
  },
  updateSchedule(data) {
    return api.put('/config/schedule', data)
  },
  getNotification() {
    return api.get('/config/notification')
  },
  updateNotification(data) {
    return api.put('/config/notification', data)
  },
  getFrequencyWords() {
    return api.get('/config/frequency-words')
  },
  updateFrequencyWords(data) {
    return api.put('/config/frequency-words', data)
  },
  exportConfig() {
    return api.get('/config/export', { responseType: 'blob' })
  },
  importConfig(formData) {
    return api.post('/config/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  getConfigDiff() {
    return api.get('/config/diff')
  },
}
