import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, unref, type MaybeRef } from 'vue'

import { apiClient } from '@/core/api/http'

export interface Task {
  id: string
  workspace_id: string
  title: string
  description: string | null
  status: string
  priority: 'low' | 'medium' | 'high' | 'urgent'
  acceptance_criteria: string[]
  assignee_user_id: string | null
  assignee_agent_role: string | null
  proof_exempt: boolean
}

export interface TaskComment {
  id: string
  task_id: string
  author_user_id: string
  author_username: string
  content: string
  created_at: string
}

export interface TaskAttachment {
  id: string
  task_id: string
  author_user_id: string
  author_username: string
  file_name: string
  url: string
  mime_type: string | null
  created_at: string
}

export interface TaskSubtask {
  id: string
  task_id: string
  workspace_id: string
  title: string
  description: string | null
  status: 'todo' | 'in_progress' | 'done'
  order: number
  assignee_user_id: string | null
  assignee_agent_role: string | null
  created_at: string
  updated_at: string
}

export interface TaskAgentTimelineItem {
  id: string
  run_id: string
  task_id: string | null
  workspace_id: string
  stage: 'router' | 'planner' | 'retrieve' | 'execute' | 'critic' | 'verifier' | 'approval_gate' | 'committer'
  agent_role: string
  title: string
  summary: string
  status: 'running' | 'completed' | 'failed' | 'abstained'
  created_at: string
  metadata: Record<string, unknown>
}

export function useTasks(workspaceId: MaybeRef<string | null>) {
  const resolvedWorkspaceId = computed(() => unref(workspaceId))
  return useQuery({
    queryKey: computed(() => ['tasks', resolvedWorkspaceId.value]),
    enabled: computed(() => Boolean(resolvedWorkspaceId.value)),
    queryFn: async () => apiClient.get(`tasks?workspace_id=${resolvedWorkspaceId.value}`).json<Task[]>(),
  })
}

export function useTaskAgentTimeline(taskId: MaybeRef<string | null>) {
  const resolvedTaskId = computed(() => unref(taskId))
  return useQuery({
    queryKey: computed(() => ['task-agent-timeline', resolvedTaskId.value]),
    enabled: computed(() => Boolean(resolvedTaskId.value)),
    queryFn: async () => apiClient.get(`tasks/${resolvedTaskId.value}/agent-timeline`).json<TaskAgentTimelineItem[]>(),
  })
}

export function useCreateTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      workspace_id: string
      title: string
      description: string
      acceptance_criteria: string[]
      status?: string
      assignee_user_id?: string
      assignee_agent_role?: string
    }) => apiClient.post('tasks', { json: payload }).json<Task>(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tasks', variables.workspace_id] })
    },
  })
}

export function useUpdateTask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      taskId: string
      workspaceId: string
      status?: string
      title?: string
      description?: string
      priority?: Task['priority']
      acceptance_criteria?: string[]
      assignee_user_id?: string | null
      assignee_agent_role?: string | null
      proof_exempt?: boolean
    }) => {
      const { taskId, ...rest } = payload
      return apiClient.patch(`tasks/${taskId}`, { json: rest }).json<Task>()
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['tasks', variables.workspaceId] })
      queryClient.invalidateQueries({ queryKey: ['task-comments', variables.taskId] })
      queryClient.invalidateQueries({ queryKey: ['task-attachments', variables.taskId] })
    },
  })
}

export function useTaskComments(taskId: MaybeRef<string | null>) {
  const resolvedTaskId = computed(() => unref(taskId))
  return useQuery({
    queryKey: computed(() => ['task-comments', resolvedTaskId.value]),
    enabled: computed(() => Boolean(resolvedTaskId.value)),
    queryFn: async () => apiClient.get(`tasks/${resolvedTaskId.value}/comments`).json<TaskComment[]>(),
  })
}

export function useAddTaskComment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { taskId: string; content: string }) =>
      apiClient.post(`tasks/${payload.taskId}/comments`, { json: { content: payload.content } }).json<TaskComment>(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['task-comments', variables.taskId] })
    },
  })
}

export function useTaskAttachments(taskId: MaybeRef<string | null>) {
  const resolvedTaskId = computed(() => unref(taskId))
  return useQuery({
    queryKey: computed(() => ['task-attachments', resolvedTaskId.value]),
    enabled: computed(() => Boolean(resolvedTaskId.value)),
    queryFn: async () => apiClient.get(`tasks/${resolvedTaskId.value}/attachments`).json<TaskAttachment[]>(),
  })
}

export function useAddTaskAttachment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { taskId: string; file_name: string; url: string; mime_type?: string }) =>
      apiClient.post(`tasks/${payload.taskId}/attachments`, { json: payload }).json<TaskAttachment>(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['task-attachments', variables.taskId] })
    },
  })
}

export function useTaskSubtasks(taskId: MaybeRef<string | null>) {
  const resolvedTaskId = computed(() => unref(taskId))
  return useQuery({
    queryKey: computed(() => ['task-subtasks', resolvedTaskId.value]),
    enabled: computed(() => Boolean(resolvedTaskId.value)),
    queryFn: async () => apiClient.get(`tasks/${resolvedTaskId.value}/subtasks`).json<TaskSubtask[]>(),
  })
}

export function useCreateTaskSubtask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      taskId: string
      title: string
      description?: string
      assignee_user_id?: string
      assignee_agent_role?: string
      order?: number
    }) => apiClient.post(`tasks/${payload.taskId}/subtasks`, { json: payload }).json<TaskSubtask[]>(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['task-subtasks', variables.taskId] })
    },
  })
}

export function useUpdateTaskSubtask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      taskId: string
      subtaskId: string
      title?: string
      description?: string
      status?: 'todo' | 'in_progress' | 'done'
      assignee_user_id?: string | null
      assignee_agent_role?: string | null
      order?: number
    }) => {
      const { taskId, subtaskId, ...body } = payload
      return apiClient.patch(`tasks/${taskId}/subtasks/${subtaskId}`, { json: body }).json<TaskSubtask[]>()
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['task-subtasks', variables.taskId] })
    },
  })
}

export function useDeleteTaskSubtask() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { taskId: string; subtaskId: string }) =>
      apiClient.delete(`tasks/${payload.taskId}/subtasks/${payload.subtaskId}`).json<TaskSubtask[]>(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['task-subtasks', variables.taskId] })
    },
  })
}

export function useRequestTaskAgentRevision() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: { taskId: string; instruction: string; stakes_level?: 'low' | 'medium' | 'high' | 'irreversible' }) =>
      apiClient
        .post(`tasks/${payload.taskId}/agent-revision`, {
          json: {
            instruction: payload.instruction,
            stakes_level: payload.stakes_level ?? 'medium',
          },
        })
        .json(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['task-agent-timeline', variables.taskId] })
      queryClient.invalidateQueries({ queryKey: ['agent-runs'] })
    },
  })
}
