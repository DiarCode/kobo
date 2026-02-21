import { useMutation } from '@tanstack/vue-query'

import { apiClient } from '@/core/api/http'

export interface CouncilSession {
  id: string
  workspace_id: string
  status: string
  stage: string
  decision: {
    id: string
    recommendation: string
    confidence: number
    dissenting_views: string[]
  }
}

export function useCreateCouncilSession() {
  return useMutation({
    mutationFn: async (payload: { workspace_id: string; question: string; task_id?: string }) =>
      apiClient.post('council/sessions', { json: payload }).json<CouncilSession>(),
  })
}
