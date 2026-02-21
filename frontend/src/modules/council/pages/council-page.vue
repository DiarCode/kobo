<script setup lang="ts">
import { computed, ref } from 'vue'
import { toast } from 'vue-sonner'

import { Button } from '@/core/components/ui/button'
import { useAuthStore } from '@/core/stores/auth.store'
import { useCreateCouncilSession } from '@/modules/council/composables/council.composable'

const authStore = useAuthStore()
authStore.init()

const workspaceId = computed(() => authStore.workspaceId)
const question = ref('Should we ship this feature this week?')
const response = ref<null | {
  recommendation: string
  confidence: number
  dissenting_views: string[]
}>(null)

const createSession = useCreateCouncilSession()

async function deliberate() {
  if (!workspaceId.value) {
    toast.error('Select workspace first')
    return
  }
  try {
    const session = await createSession.mutateAsync({
      workspace_id: workspaceId.value,
      question: question.value,
    })
    response.value = session.decision
    toast.success('Council completed')
  } catch {
    toast.error('Council run failed')
  }
}
</script>

<template>
  <div class="grid gap-6 lg:grid-cols-[0.95fr,1.05fr]">
    <section class="glass-card p-6">
      <p class="soft-chip">Council Mode</p>
      <h2 class="headline-page mt-3">Ask for decision synthesis</h2>

      <textarea v-model="question" class="mt-4 h-32" />
      <Button class="mt-3 w-full" size="lg" :disabled="createSession.isPending.value" @click="deliberate">
        Run council
      </Button>
    </section>

    <section class="glass-card p-6">
      <h3 class="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Decision Artifact</h3>
      <div v-if="response" class="mt-3 space-y-3">
        <article class="glass-card-soft p-4">
          <p class="text-xs uppercase tracking-[0.15em] text-gray-400">Recommendation</p>
          <p class="mt-1 text-base font-semibold text-gray-800">{{ response.recommendation }}</p>
        </article>
        <article class="glass-card-soft p-4">
          <p class="text-xs uppercase tracking-[0.15em] text-gray-400">Confidence</p>
          <p class="mt-1 text-2xl font-bold text-gray-800">{{ response.confidence }}</p>
        </article>
        <article class="glass-card-soft p-4">
          <p class="text-xs uppercase tracking-[0.15em] text-gray-400">Dissent</p>
          <ul class="mt-2 space-y-1 text-sm text-gray-600">
            <li v-for="(item, index) in response.dissenting_views" :key="index">{{ item }}</li>
          </ul>
        </article>
      </div>
      <p v-else class="mt-3 text-sm text-gray-500">No output yet.</p>
    </section>
  </div>
</template>
