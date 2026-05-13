import api from './index'

export const authApi = {
  register(data) {
    return api.post('/auth/register', data)
  },
  login(data) {
    return api.post('/auth/login', data)
  },
  refreshToken(data) {
    return api.post('/auth/refresh', data)
  },
  getMe() {
    return api.get('/auth/me')
  },
  changePassword(data) {
    return api.post('/auth/change-password', data)
  },
  verifyEmail(token) {
    return api.get('/auth/verify-email', { params: { token } })
  },
  forgotPassword(data) {
    return api.post('/auth/forgot-password', data)
  },
  resetPassword(token, newPassword) {
    return api.post('/auth/reset-password', null, { params: { token, new_password: newPassword } })
  },
}
