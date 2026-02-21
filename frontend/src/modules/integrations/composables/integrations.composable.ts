import { useMutation, useQuery } from '@tanstack/vue-query'

import { apiClient } from '@/core/api/http'

export function useConnectUrl(provider: 'github' | 'linear') {
  return useQuery({
    queryKey: ['integration-connect', provider],
    queryFn: async () =>
      apiClient.get(`integrations/${provider}/connect`).json<{ provider: string; authorize_url: string }>(),
  })
}

export function useCreateGithubIssue() {
  return useMutation({
    mutationFn: async (payload: {
      workspace_id: string
      task_id: string
      title: string
      description: string
    }) => apiClient.post('integrations/github/issues', { json: payload }).json<{ status: string }>(),
  })
}

export function useCreateLinearIssue() {
  return useMutation({
    mutationFn: async (payload: {
      workspace_id: string
      task_id: string
      title: string
      description: string
    }) => apiClient.post('integrations/linear/issues', { json: payload }).json<{ status: string }>(),
  })
}
