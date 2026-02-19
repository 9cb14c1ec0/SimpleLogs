import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle token refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const response = await axios.post('/api/v1/auth/refresh', {
            refresh_token: refreshToken,
          })

          const { access_token, refresh_token } = response.data
          localStorage.setItem('access_token', access_token)
          localStorage.setItem('refresh_token', refresh_token)

          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return api(originalRequest)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      }
    }

    return Promise.reject(error)
  }
)

export default api

// Types
export interface User {
  id: string
  email: string
  name: string
  is_admin: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ApiKey {
  id: string
  team_id: string
  label: string
  api_key_prefix: string
  created_at: string
}

export interface ApiKeyWithSecret extends ApiKey {
  api_key: string
}

export interface Team {
  id: string
  name: string
  api_keys: ApiKey[]
  retention_days: number | null
  created_at: string
  updated_at: string
}

export interface TeamCreateResponse extends Team {
  api_key: string
}

export interface TeamMembership {
  id: string
  user_id: string
  user_email: string
  user_name: string
  team_id: string
  role: 'viewer' | 'member' | 'manager'
  created_at: string
}

export interface Log {
  id: string
  team_id: string
  timestamp: string
  level: 'debug' | 'info' | 'warn' | 'error' | 'fatal'
  message: string
  metadata: Record<string, unknown> | null
  source: string | null
  user_id: string | null
  created_at: string
}

export interface LogSearchResult {
  items: Log[]
  total: number
  page: number
  limit: number
  pages: number
}

// Analytics types
export interface VolumeBucket {
  bucket: string
  level?: string | null
  source?: string | null
  count: number
}

export interface VolumeResponse {
  buckets: VolumeBucket[]
  totals: Record<string, number>
}

export interface TopItem {
  value: string
  count: number
}

export interface TopResponse {
  items: TopItem[]
}

export interface HeatmapCell {
  source: string
  level: string
  count: number
}

export interface HeatmapResponse {
  sources: string[]
  levels: string[]
  data: HeatmapCell[]
}

export interface TopUsersVolumeBucket {
  bucket: string
  user_id: string
  count: number
}

export interface TopUsersVolumeResponse {
  users: string[]
  buckets: TopUsersVolumeBucket[]
}
