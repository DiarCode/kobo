<script setup lang="ts">
import { computed, ref } from 'vue'
import { toast } from 'vue-sonner'

import { Button } from '@/core/components/ui/button'
import { useAuthStore } from '@/core/stores/auth.store'
import { useCreateArtifact, useArtifacts } from '@/modules/artifacts/composables/artifacts.composable'
import { useTasks } from '@/modules/tasks/composables/tasks.composable'

const authStore = useAuthStore()
authStore.init()

const workspaceId = computed(() => authStore.workspaceId)
const tasksQuery = useTasks(workspaceId)
const artifactsQuery = useArtifacts(workspaceId)
const createArtifact = useCreateArtifact()

const selectedTaskId = ref('')
const title = ref('PRD v1')
const content = ref('Acceptance criteria and rollout plan')

async function addArtifact() {
  if (!workspaceId.value || !selectedTaskId.value) {
    toast.error('Select workspace and task')
    return
  }
  try {
    await createArtifact.mutateAsync({
      workspace_id: workspaceId.value,
      task_id: selectedTaskId.value,
      type: 'spec',
      title: title.value,
      content: content.value,
      metadata: {},
    })
    toast.success('Artifact attached')
  } catch {
    toast.error('Failed to create artifact')
  }
}
</script>

<template>
  <div class="grid gap-6 lg:grid-cols-[0.9fr,1.1fr]">
    <section class="glass-card p-6">
      <p class="soft-chip">Artifact Input</p>
      <h2 class="headline-page mt-3">Proof of work</h2>

      <div class="mt-4 space-y-3">
        <select v-model="selectedTaskId">
          <option value="" disabled>Select task</option>
          <option v-for="task in tasksQuery.data.value ?? []" :key="task.id" :value="task.id">{{ task.title }}</option>
        </select>
        <input v-model="title" placeholder="Artifact title" />
        <textarea v-model="content" class="h-24" />
        <Button size="lg" class="w-full" @click="addArtifact">Attach artifact</Button>
      </div>
    </section>

    <section class="glass-card p-6">
      <h3 class="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Ledger</h3>
      <ul class="mt-3 space-y-2">
        <li
          v-for="artifact in artifactsQuery.data.value ?? []"
          :key="artifact.id"
          class="glass-card-soft px-4 py-3"
        >
          <p class="text-xs uppercase tracking-[0.16em] text-gray-400">{{ artifact.type }}</p>
          <p class="mt-1 font-semibold text-gray-800">{{ artifact.title }}</p>
          <p class="text-sm text-gray-600">{{ artifact.content }}</p>
        </li>
      </ul>
    </section>
  </div>
</template>
