import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { type User } from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => !!user.value)

  async function login(email: string, password: string) {
    loading.value = true
    try {
      const response = await api.post('/auth/login', { email, password })
      const { access_token, refresh_token } = response.data

      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)

      await fetchUser()
      return true
    } catch (error) {
      console.error('Login failed:', error)
      return false
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    try {
      await api.post('/auth/logout')
    } catch {
      // Ignore errors
    } finally {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      user.value = null
    }
  }

  async function fetchUser() {
    try {
      const response = await api.get('/auth/me')
      user.value = response.data
    } catch {
      user.value = null
    }
  }

  async function initialize() {
    const token = localStorage.getItem('access_token')
    if (token) {
      await fetchUser()
    }
  }

  return {
    user,
    loading,
    isAuthenticated,
    login,
    logout,
    fetchUser,
    initialize,
  }
})
