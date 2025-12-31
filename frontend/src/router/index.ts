import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/views/Dashboard.vue'),
    },
    {
      path: '/teams/:teamId/logs',
      name: 'logs',
      component: () => import('@/views/LogsView.vue'),
    },
    {
      path: '/admin/users',
      name: 'admin-users',
      component: () => import('@/views/admin/Users.vue'),
      meta: { requiresAdmin: true },
    },
    {
      path: '/admin/teams',
      name: 'admin-teams',
      component: () => import('@/views/admin/Teams.vue'),
      meta: { requiresAdmin: true },
    },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  // Initialize auth state on first load
  if (!authStore.user && localStorage.getItem('access_token')) {
    await authStore.initialize()
  }

  // Public routes don't require auth
  if (to.meta.public) {
    if (authStore.isAuthenticated) {
      return next('/')
    }
    return next()
  }

  // Check if authenticated
  if (!authStore.isAuthenticated) {
    return next('/login')
  }

  // Check admin requirement
  if (to.meta.requiresAdmin && !authStore.user?.is_admin) {
    return next('/')
  }

  next()
})

export default router
