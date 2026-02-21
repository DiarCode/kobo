<script setup lang="ts">
import { computed, ref } from 'vue'
import { toast } from 'vue-sonner'

import { Button } from '@/core/components/ui/button'
import { useAuthStore } from '@/core/stores/auth.store'
import {
  useConnectUrl,
  useCreateGithubIssue,
  useCreateLinearIssue,
} from '@/modules/integrations/composables/integrations.composable'
import { useTasks } from '@/modules/tasks/composables/tasks.composable'

const authStore = useAuthStore()
authStore.init()

const workspaceId = computed(() => authStore.workspaceId)
const tasksQuery = useTasks(workspaceId)

const githubConnect = useConnectUrl('github')
const linearConnect = useConnectUrl('linear')
const githubMutation = useCreateGithubIssue()
const linearMutation = useCreateLinearIssue()

const taskId = ref('')
const title = ref('KOBO generated issue')
const description = ref('Created from approved action plan')

async function create(provider: 'github' | 'linear') {
  if (!workspaceId.value || !taskId.value) {
    toast.error('Select workspace and task')
    return
  }

  try {
    if (provider === 'github') {
      await githubMutation.mutateAsync({
        workspace_id: workspaceId.value,
        task_id: taskId.value,
        title: title.value,
        description: description.value,
      })
    } else {
      await linearMutation.mutateAsync({
        workspace_id: workspaceId.value,
        task_id: taskId.value,
        title: title.value,
        description: description.value,
      })
    }
    toast.success(`${provider} action queued`)
  } catch {
    toast.error(`Failed to queue ${provider} action`)
  }
}
</script>

<template>
  <div class="grid gap-6 lg:grid-cols-[0.9fr,1.1fr]">
    <section class="glass-card p-6">
      <p class="soft-chip">OAuth Integrations</p>
      <h2 class="headline-page mt-3">Connect channels</h2>

      <div class="mt-4 space-y-2">
        <a
          :href="githubConnect.data.value?.authorize_url"
          target="_blank"
          class="glass-card-soft block px-4 py-3 text-sm font-semibold text-gray-600"
        >
          Connect GitHub
        </a>
        <a
          :href="linearConnect.data.value?.authorize_url"
          target="_blank"
          class="glass-card-soft block px-4 py-3 text-sm font-semibold text-gray-600"
        >
          Connect Linear
        </a>
      </div>
    </section>

    <section class="glass-card p-6">
      <h3 class="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Queue action</h3>
      <div class="mt-3 space-y-3">
        <select v-model="taskId">
          <option value="" disabled>Select task</option>
          <option v-for="task in tasksQuery.data.value ?? []" :key="task.id" :value="task.id">{{ task.title }}</option>
        </select>
        <input v-model="title" />
        <textarea v-model="description" class="h-24" />
        <div class="grid grid-cols-2 gap-2">
          <Button variant="outline" @click="create('github')">GitHub</Button>
          <Button variant="outline" @click="create('linear')">Linear</Button>
        </div>
      </div>
    </section>
  </div>
</template>
