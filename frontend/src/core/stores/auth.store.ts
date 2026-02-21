import { defineStore } from 'pinia'

import { apiClient } from '@/core/api/http'

export interface AuthUser {
  id: string
  username: string
}

interface AuthState {
  user: AuthUser | null
  workspaceId: string | null
  sessionChecked: boolean
  workspaceValidated: boolean
}

const WORKSPACE_STORAGE_PREFIX = 'kobo.workspace.'
const LEGACY_STORAGE_KEY = 'kobo.auth'

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    user: null,
    workspaceId: null,
    sessionChecked: false,
    workspaceValidated: false,
  }),
  actions: {
    init() {
      // Workspace selection is loaded only after resolving current user
      // to avoid cross-user leakage from stale local state.
      if (localStorage.getItem(LEGACY_STORAGE_KEY)) {
        localStorage.removeItem(LEGACY_STORAGE_KEY)
      }
    },
    async hydrateSession() {
      if (this.sessionChecked) return
      try {
        const user = await apiClient.get('auth/me').json<AuthUser>()
        this.user = user
        this.workspaceId = localStorage.getItem(`${WORKSPACE_STORAGE_PREFIX}${user.id}`)
        this.workspaceValidated = false
      } catch {
        this.user = null
        this.workspaceId = null
      } finally {
        this.sessionChecked = true
      }
    },
    setUser(user: AuthUser | null) {
      const previousUserId = this.user?.id ?? null
      this.user = user
      this.sessionChecked = true
      this.workspaceValidated = false
      if (!user) {
        this.workspaceId = null
        return
      }
      if (previousUserId !== user.id) {
        this.workspaceId = localStorage.getItem(`${WORKSPACE_STORAGE_PREFIX}${user.id}`)
      }
    },
    setWorkspace(workspaceId: string | null) {
      this.workspaceId = workspaceId
      this.workspaceValidated = true
      this.persist()
    },
    async validateWorkspaceSelection() {
      if (this.workspaceValidated) return
      if (!this.user || !this.workspaceId) {
        this.workspaceValidated = true
        return
      }
      try {
        await apiClient.get(`workspaces/${this.workspaceId}`).json()
      } catch (error) {
        const maybe = error as { response?: { status?: number } }
        const status = maybe.response?.status
        if (status === 403 || status === 404) {
          this.workspaceId = null
          this.persist()
        }
      } finally {
        this.workspaceValidated = true
      }
    },
    async logout() {
      try {
        await apiClient.post('auth/logout').json<{ message: string }>()
      } catch {
        // Session cleanup must be resilient; clear local state regardless.
      }
      this.user = null
      this.workspaceId = null
      this.sessionChecked = true
      this.workspaceValidated = false
    },
    persist() {
      const userId = this.user?.id
      if (!userId) return
      const key = `${WORKSPACE_STORAGE_PREFIX}${userId}`
      if (this.workspaceId) {
        localStorage.setItem(key, this.workspaceId)
      } else {
        localStorage.removeItem(key)
      }
    },
  },
})
