import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { guest: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { guest: true },
  },
  {
    path: '/verify-email',
    name: 'VerifyEmail',
    component: () => import('@/views/VerifyEmail.vue'),
    meta: { guest: true },
  },
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: () => import('@/views/ResetPassword.vue'),
    meta: { guest: true },
  },
  {
    path: '/pricing',
    name: 'Pricing',
    component: () => import('@/views/Pricing.vue'),
  },
  {
    path: '/privacy-policy',
    name: 'PrivacyPolicy',
    component: () => import('@/views/PrivacyPolicy.vue'),
  },
  {
    path: '/terms-of-service',
    name: 'TermsOfService',
    component: () => import('@/views/TermsOfService.vue'),
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard',
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
      },
      {
        path: 'config',
        name: 'Config',
        component: () => import('@/views/Config.vue'),
      },
      {
        path: 'news',
        name: 'News',
        component: () => import('@/views/News.vue'),
      },
      {
        path: 'tasks',
        name: 'Tasks',
        component: () => import('@/views/Tasks.vue'),
      },
      {
        path: 'task-history',
        name: 'TaskHistory',
        component: () => import('@/views/TaskHistory.vue'),
      },
      {
        path: 'account',
        name: 'Account',
        component: () => import('@/views/Account.vue'),
      },
      {
        path: 'users',
        name: 'UsersManagement',
        component: () => import('@/views/UsersManagement.vue'),
        meta: { requiresAdmin: true },
      },
      {
        path: 'purchase',
        name: 'Purchase',
        component: () => import('@/views/Purchase.vue'),
      },
      {
        path: 'orders',
        name: 'Orders',
        component: () => import('@/views/Orders.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth && !authStore.token) {
    return { name: 'Login' }
  }
  
  if (to.meta.guest && authStore.token) {
    return { name: 'Dashboard' }
  }
  
  if (to.meta.requiresAuth && !authStore.user) {
    try {
      await authStore.fetchUser()
    } catch {
      return { name: 'Login' }
    }
  }

  if (to.meta.requiresAdmin) {
    if (!authStore.user || authStore.user.is_superuser !== true) {
      return { name: 'Dashboard' }
    }
  }
})

export default router
