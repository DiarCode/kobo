import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, unref, type MaybeRef } from 'vue'

import { apiClient } from '@/core/api/http'

export interface AgentRole {
  key: string
  display_name: string
}

export interface AgentRun {
  id: string
  role_key: string
  status: string
  task_id: string | null
  created_at: string
  output?: {
    executive_summary: string
    confidence_score: number
    full_content: string
  }
}

export interface AgentRunTimelineItem {
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

export function useAgentRoles() {
  return useQuery({
    queryKey: ['agent-roles'],
    queryFn: async () => apiClient.get('agents').json<{ roles: AgentRole[] }>(),
  })
}

export function useAgentRunTimeline(runId: MaybeRef<string | null>) {
  const resolvedRunId = computed(() => unref(runId))
  return useQuery({
    queryKey: computed(() => ['agent-run-timeline', resolvedRunId.value]),
    enabled: computed(() => Boolean(resolvedRunId.value)),
    queryFn: async () => apiClient.get(`agent-runs/${resolvedRunId.value}/timeline`).json<AgentRunTimelineItem[]>(),
  })
}

export function useAgentRuns(workspaceId: MaybeRef<string | null>) {
  const resolvedWorkspaceId = computed(() => unref(workspaceId))
  return useQuery({
    queryKey: computed(() => ['agent-runs', resolvedWorkspaceId.value]),
    enabled: computed(() => Boolean(resolvedWorkspaceId.value)),
    queryFn: async () => apiClient.get(`agent-runs?workspace_id=${resolvedWorkspaceId.value}`).json<AgentRun[]>(),
  })
}

export function useRunAgent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      workspace_id: string
      task_id?: string
      role_key: string
      goal: string
      stakes_level: 'low' | 'medium' | 'high' | 'irreversible'
    }) => apiClient.post('agent-runs', { json: payload }).json<AgentRun>(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['agent-runs', variables.workspace_id] })
    },
  })
}
