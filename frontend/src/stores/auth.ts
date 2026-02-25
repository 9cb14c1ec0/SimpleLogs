import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { startAuthentication } from '@simplewebauthn/browser'
import api, { type User, type LoginResponse } from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const loading = ref(false)
  const totpRequired = ref(false)
  const totpToken = ref<string | null>(null)

  const isAuthenticated = computed(() => !!user.value)

  async function login(email: string, password: string): Promise<'success' | 'totp_required' | 'error'> {
    loading.value = true
    try {
      const response = await api.post<LoginResponse>('/auth/login', { email, password })
      const data = response.data

      if (data.totp_required) {
        totpRequired.value = true
        totpToken.value = data.totp_token
        return 'totp_required'
      }

      localStorage.setItem('access_token', data.access_token!)
      localStorage.setItem('refresh_token', data.refresh_token!)
      await fetchUser()
      return 'success'
    } catch (error) {
      console.error('Login failed:', error)
      return 'error'
    } finally {
      loading.value = false
    }
  }

  async function verifyTotp(code: string): Promise<boolean> {
    loading.value = true
    try {
      const response = await api.post('/auth/verify-totp', {
        totp_token: totpToken.value,
        code,
      })
      const { access_token, refresh_token } = response.data

      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)

      totpRequired.value = false
      totpToken.value = null

      await fetchUser()
      return true
    } catch (error) {
      console.error('TOTP verification failed:', error)
      return false
    } finally {
      loading.value = false
    }
  }

  function clearTotpState() {
    totpRequired.value = false
    totpToken.value = null
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
      clearTotpState()
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

  async function loginWithPasskey(): Promise<'success' | 'error' | 'cancelled'> {
    loading.value = true
    try {
      const optionsResp = await api.post('/auth/passkeys/authenticate/options')
      const { options, challenge_id } = optionsResp.data

      let assertion
      try {
        assertion = await startAuthentication({ optionsJSON: JSON.parse(options) })
      } catch {
        return 'cancelled'
      }

      const verifyResp = await api.post<LoginResponse>('/auth/passkeys/authenticate/verify', {
        credential: JSON.stringify(assertion),
        challenge_id,
      })
      const data = verifyResp.data

      localStorage.setItem('access_token', data.access_token!)
      localStorage.setItem('refresh_token', data.refresh_token!)
      await fetchUser()
      return 'success'
    } catch (error) {
      console.error('Passkey login failed:', error)
      return 'error'
    } finally {
      loading.value = false
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
    totpRequired,
    totpToken,
    isAuthenticated,
    login,
    loginWithPasskey,
    verifyTotp,
    clearTotpState,
    logout,
    fetchUser,
    initialize,
  }
})
