import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, unref, type MaybeRef } from 'vue'

import { apiClient } from '@/core/api/http'

export interface StreamEvent {
  type: 'start' | 'token' | 'complete' | 'error'
  content?: string
  response?: string
  model_used?: string
  message_id?: string
  message?: string
}

export interface AssistantHistoryItem {
  id: string
  workspace_id: string
  user_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  metadata: Record<string, unknown>
}

export interface AssistantChatResponse {
  message_id: string
  workspace_id: string
  response: string
  used_context: string[]
  model?: string | null
  fallback_used?: boolean
  warning?: string | null
  created_at: string
}

export interface AssistantVoiceToken {
  workspace_id: string
  identity: string
  room: string
  token: string
  livekit_url: string
}

export function useAssistantHistory(workspaceId: MaybeRef<string | null>) {
  const resolvedWorkspaceId = computed(() => unref(workspaceId))
  return useQuery({
    queryKey: computed(() => ['assistant-history', resolvedWorkspaceId.value]),
    enabled: computed(() => Boolean(resolvedWorkspaceId.value)),
    queryFn: async () =>
      apiClient.get(`assistant/workspaces/${resolvedWorkspaceId.value}/history`).json<AssistantHistoryItem[]>(),
    refetchInterval: 5000,
  })
}

export function useAssistantChat() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      workspaceId: string
      message: string
      task_id?: string
      include_history?: boolean
    }) =>
      apiClient
        .post(`assistant/workspaces/${payload.workspaceId}/chat`, {
          json: {
            message: payload.message,
            task_id: payload.task_id,
            include_history: payload.include_history ?? true,
          },
        })
        .json<AssistantChatResponse>(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['assistant-history', variables.workspaceId] })
    },
  })
}

export function useAssistantVoiceToken() {
  return useMutation({
    mutationFn: async (workspaceId: string) =>
      apiClient.post(`assistant/workspaces/${workspaceId}/voice/token`).json<AssistantVoiceToken>(),
  })
}

export async function* streamAssistantChat(payload: {
  workspaceId: string
  message: string
  task_id?: string
  include_history?: boolean
}): AsyncGenerator<StreamEvent, void, unknown> {
  const response = await apiClient.post(`assistant/workspaces/${payload.workspaceId}/chat/stream`, {
    json: {
      message: payload.message,
      task_id: payload.task_id,
      include_history: payload.include_history ?? true,
    },
  })

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('No response body')
  }

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6)) as StreamEvent
            yield event
          } catch {
            // Skip invalid JSON
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}
