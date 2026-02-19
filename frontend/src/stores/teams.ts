import { defineStore } from 'pinia'
import { ref } from 'vue'
import api, { type Team, type TeamMembership, type ApiKey, type ApiKeyWithSecret } from '@/api/client'

export const useTeamsStore = defineStore('teams', () => {
  const teams = ref<Team[]>([])
  const currentTeam = ref<Team | null>(null)
  const loading = ref(false)

  async function fetchTeams() {
    loading.value = true
    try {
      const response = await api.get('/admin/teams')
      teams.value = response.data
    } catch (error) {
      console.error('Failed to fetch teams:', error)
    } finally {
      loading.value = false
    }
  }

  async function createTeam(name: string, retentionDays: number | null) {
    const response = await api.post('/admin/teams', {
      name,
      retention_days: retentionDays,
    })
    teams.value.push(response.data)
    return response.data
  }

  async function updateTeam(id: string, data: { name?: string; retention_days?: number | null }) {
    const response = await api.put(`/admin/teams/${id}`, data)
    const index = teams.value.findIndex(t => t.id === id)
    if (index >= 0) {
      teams.value[index] = response.data
    }
    return response.data
  }

  async function deleteTeam(id: string) {
    await api.delete(`/admin/teams/${id}`)
    teams.value = teams.value.filter(t => t.id !== id)
  }

  async function getApiKeys(teamId: string): Promise<ApiKey[]> {
    const response = await api.get(`/admin/teams/${teamId}/api-keys`)
    return response.data
  }

  async function createApiKey(teamId: string, label?: string, apiKey?: string): Promise<ApiKeyWithSecret> {
    const body: Record<string, string> = {}
    if (label) body.label = label
    if (apiKey) body.api_key = apiKey
    const response = await api.post(`/admin/teams/${teamId}/api-keys`, body)
    return response.data
  }

  async function deleteApiKey(teamId: string, keyId: string) {
    await api.delete(`/admin/teams/${teamId}/api-keys/${keyId}`)
  }

  async function getMembers(teamId: string): Promise<TeamMembership[]> {
    const response = await api.get(`/admin/teams/${teamId}/members`)
    return response.data
  }

  async function addMember(teamId: string, userId: string, role: string) {
    const response = await api.post(`/admin/teams/${teamId}/members`, {
      user_id: userId,
      role,
    })
    return response.data
  }

  async function removeMember(teamId: string, userId: string) {
    await api.delete(`/admin/teams/${teamId}/members/${userId}`)
  }

  function selectTeam(team: Team | null) {
    currentTeam.value = team
  }

  return {
    teams,
    currentTeam,
    loading,
    fetchTeams,
    createTeam,
    updateTeam,
    deleteTeam,
    getApiKeys,
    createApiKey,
    deleteApiKey,
    getMembers,
    addMember,
    removeMember,
    selectTeam,
  }
})
