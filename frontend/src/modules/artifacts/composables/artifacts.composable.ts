import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, unref, type MaybeRef } from 'vue'

import { apiClient } from '@/core/api/http'

export interface Artifact {
  id: string
  workspace_id: string
  task_id: string | null
  type: string
  title: string
  content: string
  created_at: string
}

export function useArtifacts(workspaceId: MaybeRef<string | null>) {
  const resolvedWorkspaceId = computed(() => unref(workspaceId))
  return useQuery({
    queryKey: computed(() => ['artifacts', resolvedWorkspaceId.value]),
    enabled: computed(() => Boolean(resolvedWorkspaceId.value)),
    queryFn: async () =>
      apiClient.get(`artifacts?workspace_id=${resolvedWorkspaceId.value}`).json<Artifact[]>(),
  })
}

export function useCreateArtifact() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: {
      workspace_id: string
      task_id: string
      type: string
      title: string
      content: string
      metadata: Record<string, unknown>
    }) => apiClient.post('artifacts', { json: payload }).json<Artifact>(),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['artifacts', variables.workspace_id] })
    },
  })
}
