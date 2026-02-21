<script setup lang="ts">
import { computed, ref } from 'vue'
import { toast } from 'vue-sonner'

import { Button } from '@/core/components/ui/button'
import { useAuthStore } from '@/core/stores/auth.store'
import { useAgentRoles, useAgentRuns, useRunAgent } from '@/modules/agents/composables/agents.composable'
import { useTasks } from '@/modules/tasks/composables/tasks.composable'

const authStore = useAuthStore()
authStore.init()

const workspaceId = computed(() => authStore.workspaceId)
const roleKey = ref('pm')
const taskId = ref('')
const goal = ref('Generate a scoped implementation plan and risk checklist.')

const rolesQuery = useAgentRoles()
const runsQuery = useAgentRuns(workspaceId)
const tasksQuery = useTasks(workspaceId)
const runAgent = useRunAgent()

async function launchRun() {
  if (!workspaceId.value) {
    toast.error('Select workspace first')
    return
  }
  try {
    await runAgent.mutateAsync({
      workspace_id: workspaceId.value,
      task_id: taskId.value || undefined,
      role_key: roleKey.value,
      goal: goal.value,
      stakes_level: 'medium',
    })
    toast.success('Agent run completed')
  } catch {
    toast.error('Agent run failed')
  }
}
</script>

<template>
  <div class="grid gap-6 xl:grid-cols-[0.9fr,1.1fr]">
    <section class="glass-card p-6">
      <p class="soft-chip">Runtime</p>
      <h2 class="headline-page mt-3">Launch agent run</h2>

      <div class="mt-4 space-y-3">
        <select v-model="roleKey">
          <option v-for="role in rolesQuery.data.value?.roles ?? []" :key="role.key" :value="role.key">
            {{ role.display_name }}
          </option>
        </select>
        <select v-model="taskId">
          <option value="">No task link</option>
          <option v-for="task in tasksQuery.data.value ?? []" :key="task.id" :value="task.id">{{ task.title }}</option>
        </select>
        <textarea v-model="goal" class="h-28" />
        <Button class="w-full" size="lg" :disabled="runAgent.isPending.value" @click="launchRun">Run agent</Button>
      </div>
    </section>

    <section class="glass-card p-6">
      <h3 class="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Recent Runs</h3>
      <ul class="mt-3 space-y-2">
        <li v-for="run in runsQuery.data.value ?? []" :key="run.id" class="glass-card-soft px-4 py-3">
          <div class="flex items-center justify-between">
            <p class="font-semibold text-gray-800">{{ run.role_key }}</p>
            <p class="rounded-full bg-white/80 px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-gray-500">
              {{ run.status }}
            </p>
          </div>
          <p class="mt-2 text-sm text-gray-600">{{ run.output?.executive_summary ?? 'No summary' }}</p>
          <p class="mt-1 text-xs text-gray-500">Confidence: {{ run.output?.confidence_score ?? 'n/a' }}</p>
        </li>
      </ul>
    </section>
  </div>
</template>
