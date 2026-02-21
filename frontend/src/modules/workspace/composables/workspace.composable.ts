import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, unref, type MaybeRef } from 'vue'

import { apiClient } from '@/core/api/http'

export interface Workspace {
  id: string
  name: string
  slug: string
  description: string | null
  template: string | null
  invite_token: string | null
  created_at: string
}

export interface WorkspaceMember {
  workspace_id: string
  user_id: string
  username: string | null
  nickname: string | null
  avatar_key: string | null
  role: 'owner' | 'admin' | 'member'
}

export interface WorkspaceAgent {
  id: string
  workspace_id: string
  role_key: string
  full_name: string
  system_prompt: string
  tone: string
  character: string
  avatar_key: string
  status: 'offline' | 'online' | 'working' | 'idle'
  created_at: string
}

export interface AgentRoleTemplate {
  key: string
  display_name: string
  title: string
  tone: string
  character: string
  system_prompt: string
  avatar_key: string
}

export interface WorkspaceProfile {
  workspace_id: string
  user_id: string
  nickname: string
  avatar_key: string
  updated_at: string
}

export interface WorkspaceInvite {
  workspace_id: string
  token: string
  invite_url: string
  created_at: string
  revoked: boolean
}

export interface WorkspaceTaskStatus {
  key: string
  label: string
  order: number
  is_default: boolean
}

export interface WorkspaceFile {
  id: string
  workspace_id: string
  name: string
  url: string
  type: string
  uploaded_by_user_id: string
  created_at: string
}

export interface WorkspaceActionRequired {
  id: string
  workspace_id: string
  title: string
  description: string
  severity: 'low' | 'medium' | 'high'
  status: 'open' | 'acknowledged' | 'done'
  created_at: string
}

export function useWorkspaces() {
  return useQuery({
    queryKey: ['workspaces'],
    queryFn: async () => apiClient.get('workspaces').json<Workspace[]>(),
  })
}

export function useWorkspace(workspaceId: MaybeRef<string | null>) {
  const resolvedWorkspaceId = computed(() => unref(workspaceId))
  return useQuery({
    queryKey: computed(() => ['workspace', resolvedWorkspaceId.value]),
    enabled: computed(() => Boolean(resolvedWorkspaceId.value)),
    queryFn: async () => apiClient.get(`workspaces/${resolvedWorkspaceId.value}`).json<Workspace>(),
  })
}

export function useCreateWorkspace() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      name: string
      slug: string
      description?: string
      template?: string
    }) => apiClient.post('workspaces', { json: payload }).json<Workspace>(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
    },
  })
}

export function useWorkspaceMembers(workspaceId: MaybeRef<string | null>) {
  const resolvedWorkspaceId = computed(() => unref(workspaceId))
  return useQuery({
    queryKey: computed(() => ['workspace-members', resolvedWorkspaceId.value]),
    enabled: computed(() => Boolean(resolvedWorkspaceId.value)),
    queryFn: async () => apiClient.get(`workspaces/${resolvedWorkspaceId.value}/members`).json<WorkspaceMember[]>(),
  })
}

export function useRemoveWorkspaceMember() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { workspaceId: string; memberUserId: string }) =>
      apiClient.delete(`workspaces/${payload.workspaceId}/members/${payload.memberUserId}`).json<{ message: string }>(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workspace-members', variables.workspaceId] })
    },
  })
}

export function useWorkspaceProfile(workspaceId: MaybeRef<string | null>) {
  const resolvedWorkspaceId = computed(() => unref(workspaceId))
  return useQuery({
    queryKey: computed(() => ['workspace-profile', resolvedWorkspaceId.value]),
    enabled: computed(() => Boolean(resolvedWorkspaceId.value)),
    queryFn: async () => apiClient.get(`workspaces/${resolvedWorkspaceId.value}/me/profile`).json<WorkspaceProfile>(),
  })
}

export function useUpdateWorkspaceProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { workspaceId: string; nickname: string; avatar_key: string }) =>
      apiClient.patch(`workspaces/${payload.workspaceId}/me/profile`, { json: payload }).json<WorkspaceProfile>(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workspace-profile', variables.workspaceId] })
      queryClient.invalidateQueries({ queryKey: ['workspace-members', variables.workspaceId] })
    },
  })
}

export function useWorkspaceInvite(workspaceId: MaybeRef<string | null>) {
  const resolvedWorkspaceId = computed(() => unref(workspaceId))
  return useQuery({
    queryKey: computed(() => ['workspace-invite', resolvedWorkspaceId.value]),
    enabled: computed(() => Boolean(resolvedWorkspaceId.value)),
    queryFn: async () => apiClient.get(`workspaces/${resolvedWorkspaceId.value}/invite-link`).json<WorkspaceInvite>(),
  })
}

export function useRefreshWorkspaceInvite() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (workspaceId: string) =>
      apiClient.post(`workspaces/${workspaceId}/invite-link/refresh`).json<WorkspaceInvite>(),
    onSuccess: (_, workspaceId) => {
      queryClient.invalidateQueries({ queryKey: ['workspace-invite', workspaceId] })
      queryClient.invalidateQueries({ queryKey: ['workspace', workspaceId] })
    },
  })
}

export function useInvitation(token: MaybeRef<string | null>) {
  const resolvedToken = computed(() => unref(token))
  return useQuery({
    queryKey: computed(() => ['invitation', resolvedToken.value]),
    enabled: computed(() => Boolean(resolvedToken.value)),
    queryFn: async () => apiClient.get(`workspaces/invitations/${resolvedToken.value}`).json<Workspace>(),
  })
}

export function useAcceptInvitation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (token: string) => apiClient.post(`workspaces/invitations/${token}/accept`).json<Workspace>(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
    },
  })
}

export function useWorkspaceAgents(workspaceId: MaybeRef<string | null>) {
  const resolvedWorkspaceId = computed(() => unref(workspaceId))
  return useQuery({
    queryKey: computed(() => ['workspace-agents', resolvedWorkspaceId.value]),
    enabled: computed(() => Boolean(resolvedWorkspaceId.value)),
    queryFn: async () => apiClient.get(`workspaces/${resolvedWorkspaceId.value}/agents`).json<WorkspaceAgent[]>(),
  })
}

export function useAgentRoleTemplates() {
  return useQuery({
    queryKey: ['agent-role-templates'],
    queryFn: async () => apiClient.get('agents').json<{ roles: AgentRoleTemplate[] }>(),
  })
}

export function useBootstrapWorkspaceAgents() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      workspaceId: string
      agents: Array<{
        role_key: string
        full_name?: string
        tone?: string
        character?: string
        system_prompt?: string
        avatar_key?: string
        status?: 'offline' | 'online' | 'working' | 'idle'
      }>
    }) =>
      apiClient
        .post(`workspaces/${payload.workspaceId}/agents/bootstrap`, {
          json: { agents: payload.agents },
        })
        .json<WorkspaceAgent[]>(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workspace-agents', variables.workspaceId] })
    },
  })
}

export function useUpdateWorkspaceAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      workspaceId: string
      agentId: string
      status?: 'offline' | 'online' | 'working' | 'idle'
      full_name?: string
      tone?: string
      character?: string
      system_prompt?: string
      avatar_key?: string
    }) => {
      const { workspaceId, agentId, ...body } = payload
      return apiClient.patch(`workspaces/${workspaceId}/agents/${agentId}`, { json: body }).json<WorkspaceAgent>()
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workspace-agents', variables.workspaceId] })
    },
  })
}

export function useCreateWorkspaceAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      workspaceId: string
      role_key: string
      full_name?: string
      tone?: string
      character?: string
      system_prompt?: string
      avatar_key?: string
      status?: 'offline' | 'online' | 'working' | 'idle'
    }) => {
      const { workspaceId, ...body } = payload
      return apiClient.post(`workspaces/${workspaceId}/agents`, { json: body }).json<WorkspaceAgent>()
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workspace-agents', variables.workspaceId] })
    },
  })
}

export function useDeleteWorkspaceAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { workspaceId: string; agentId: string }) =>
      apiClient.delete(`workspaces/${payload.workspaceId}/agents/${payload.agentId}`).json<{ message: string }>(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workspace-agents', variables.workspaceId] })
    },
  })
}

export function useWorkspaceTaskStatuses(workspaceId: MaybeRef<string | null>) {
  const resolvedWorkspaceId = computed(() => unref(workspaceId))
  return useQuery({
    queryKey: computed(() => ['workspace-task-statuses', resolvedWorkspaceId.value]),
    enabled: computed(() => Boolean(resolvedWorkspaceId.value)),
    queryFn: async () =>
      apiClient.get(`workspaces/${resolvedWorkspaceId.value}/task-statuses`).json<WorkspaceTaskStatus[]>(),
  })
}

export function useAddWorkspaceTaskStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { workspaceId: string; key: string; label: string }) =>
      apiClient.post(`workspaces/${payload.workspaceId}/task-statuses`, { json: payload }).json<WorkspaceTaskStatus[]>(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workspace-task-statuses', variables.workspaceId] })
    },
  })
}

export function useRemoveWorkspaceTaskStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { workspaceId: string; statusKey: string }) =>
      apiClient.delete(`workspaces/${payload.workspaceId}/task-statuses/${payload.statusKey}`).json<WorkspaceTaskStatus[]>(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workspace-task-statuses', variables.workspaceId] })
      queryClient.invalidateQueries({ queryKey: ['tasks', variables.workspaceId] })
    },
  })
}

export function useUpdateWorkspaceTaskStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { workspaceId: string; statusKey: string; label?: string; order?: number }) =>
      apiClient
        .patch(`workspaces/${payload.workspaceId}/task-statuses/${payload.statusKey}`, {
          json: { label: payload.label, order: payload.order },
        })
        .json<WorkspaceTaskStatus[]>(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workspace-task-statuses', variables.workspaceId] })
    },
  })
}

export function useWorkspaceFiles(workspaceId: MaybeRef<string | null>) {
  const resolvedWorkspaceId = computed(() => unref(workspaceId))
  return useQuery({
    queryKey: computed(() => ['workspace-files', resolvedWorkspaceId.value]),
    enabled: computed(() => Boolean(resolvedWorkspaceId.value)),
    queryFn: async () => apiClient.get(`workspaces/${resolvedWorkspaceId.value}/files`).json<WorkspaceFile[]>(),
  })
}

export function useCreateWorkspaceFile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { workspaceId: string; name: string; url: string; type: string }) =>
      apiClient.post(`workspaces/${payload.workspaceId}/files`, { json: payload }).json<WorkspaceFile>(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workspace-files', variables.workspaceId] })
    },
  })
}

export function useUploadWorkspaceFile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { workspaceId: string; file: File }) => {
      const formData = new FormData()
      formData.set('file', payload.file)
      return apiClient.post(`workspaces/${payload.workspaceId}/files/upload`, { body: formData }).json<WorkspaceFile>()
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workspace-files', variables.workspaceId] })
      queryClient.invalidateQueries({ queryKey: ['search'] })
    },
  })
}

export function useWorkspaceActionsRequired(workspaceId: MaybeRef<string | null>) {
  const resolvedWorkspaceId = computed(() => unref(workspaceId))
  return useQuery({
    queryKey: computed(() => ['workspace-actions-required', resolvedWorkspaceId.value]),
    enabled: computed(() => Boolean(resolvedWorkspaceId.value)),
    queryFn: async () =>
      apiClient.get(`workspaces/${resolvedWorkspaceId.value}/actions-required`).json<WorkspaceActionRequired[]>(),
  })
}

export function useCreateWorkspaceActionRequired() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      workspaceId: string
      title: string
      description: string
      severity: 'low' | 'medium' | 'high'
    }) =>
      apiClient.post(`workspaces/${payload.workspaceId}/actions-required`, { json: payload }).json<WorkspaceActionRequired>(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workspace-actions-required', variables.workspaceId] })
    },
  })
}

export function useUpdateWorkspaceActionRequired() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      workspaceId: string
      actionId: string
      status: 'open' | 'acknowledged' | 'done'
    }) =>
      apiClient
        .patch(`workspaces/${payload.workspaceId}/actions-required/${payload.actionId}`, { json: payload })
        .json<WorkspaceActionRequired>(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workspace-actions-required', variables.workspaceId] })
    },
  })
}

export function useUpdateWorkspaceSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      workspaceId: string
      name?: string
      description?: string
      template?: string
    }) => {
      const { workspaceId, ...body } = payload
      return apiClient.patch(`workspaces/${workspaceId}/settings`, { json: body }).json<Workspace>()
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workspace', variables.workspaceId] })
      queryClient.invalidateQueries({ queryKey: ['workspaces'] })
    },
  })
}
