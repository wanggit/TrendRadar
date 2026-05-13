import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('access_token') || '')

  const isTrialActive = computed(() => {
    if (!user.value || user.value.tier !== 'pro') return false
    if (!user.value.trial_end_at) return false
    return new Date(user.value.trial_end_at) > new Date()
  })

  const trialDaysLeft = computed(() => {
    if (!isTrialActive.value) return null
    const end = new Date(user.value.trial_end_at)
    const now = new Date()
    const diff = Math.ceil((end - now) / (1000 * 60 * 60 * 24))
    return Math.max(0, diff)
  })

  const isTrialExpiringSoon = computed(() => {
    const days = trialDaysLeft.value
    return days !== null && days <= 3
  })

  const isTrialExpired = computed(() => {
    if (!user.value || user.value.tier !== 'pro') return false
    if (!user.value.trial_end_at) return false
    return new Date(user.value.trial_end_at) <= new Date()
  })

  const isPaidPro = computed(() => {
    return user.value?.tier === 'pro' && user.value.trial_used && !isTrialActive.value && user.value.expire_at
  })

  async function login(credentials) {
    const data = await authApi.login(credentials)
    token.value = data.access_token
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    await fetchUser()
    router.push('/dashboard')
  }

  async function register(data) {
    await authApi.register(data)
    await login({ email: data.email, password: data.password })
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      user.value = await authApi.getMe()
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    router.push('/login')
  }

  return { user, token, login, register, fetchUser, logout, isTrialActive, trialDaysLeft, isTrialExpiringSoon, isTrialExpired, isPaidPro }
})
