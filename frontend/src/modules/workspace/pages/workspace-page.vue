<script setup lang="ts">
import { useRouter } from 'vue-router'

import { Button } from '@/core/components/ui/button'
import { useAuthStore } from '@/core/stores/auth.store'
import { useWorkspaces } from '@/modules/workspace/composables/workspace.composable'

const router = useRouter()
const authStore = useAuthStore()
authStore.init()

const workspacesQuery = useWorkspaces()

async function enterWorkspace(workspaceId: string) {
  authStore.setWorkspace(workspaceId)
  await router.push('/office')
}

async function createWorkspace() {
  await router.push('/workspace/create')
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center px-4">
    <section class="w-full max-w-2xl rounded-3xl border border-white/10 bg-[#141414]/90 p-8 shadow-2xl shadow-black/50 backdrop-blur-xl">
      <div class="mb-6 flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-white">Your Workspaces</h1>
          <p class="mt-1 text-sm text-gray-400">Select one to continue.</p>
        </div>
        <Button @click="createWorkspace">Create</Button>
      </div>

      <div v-if="workspacesQuery.isLoading.value" class="rounded-2xl border border-white/10 bg-[#111111] p-4 text-sm text-gray-400">
        Loading...
      </div>

      <div v-else-if="(workspacesQuery.data.value?.length ?? 0) === 0" class="rounded-2xl border border-white/10 bg-[#111111] p-6 text-center">
        <p class="text-sm text-gray-300">No workspaces yet.</p>
        <Button class="mt-4" @click="createWorkspace">Create first workspace</Button>
      </div>

      <ul v-else class="space-y-3">
        <li
          v-for="workspace in workspacesQuery.data.value ?? []"
          :key="workspace.id"
          class="flex items-center justify-between rounded-2xl border border-white/10 bg-[#111111] px-4 py-3"
        >
          <div>
            <p class="font-semibold text-white">{{ workspace.name }}</p>
            <p class="text-xs text-gray-400">{{ workspace.description || 'No description' }}</p>
          </div>
          <Button variant="outline" @click="enterWorkspace(workspace.id)">Enter</Button>
        </li>
      </ul>
    </section>
  </div>
</template>
