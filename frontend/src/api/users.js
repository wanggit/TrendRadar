import api from './index'

export const usersApi = {
  list(params = {}) {
    return api.get('/users/', { params })
  },
  create(data) {
    return api.post('/users/', data)
  },
  get(id) {
    return api.get(`/users/${id}`)
  },
  update(id, data) {
    return api.put(`/users/${id}`, data)
  },
  delete(id) {
    return api.delete(`/users/${id}`)
  },
  resetPassword(id) {
    return api.post(`/users/${id}/reset-password`)
  },
}
