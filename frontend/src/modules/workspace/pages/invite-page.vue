<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { Button } from '@/core/components/ui/button'
import { useAuthStore } from '@/core/stores/auth.store'
import { AVATAR_OPTIONS } from '@/modules/workspace/constants/avatar-options'
import {
  useAcceptInvitation,
  useInvitation,
  useUpdateWorkspaceProfile,
} from '@/modules/workspace/composables/workspace.composable'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
authStore.init()

const token = computed(() => String(route.params.token ?? ''))
const invitationQuery = useInvitation(token)
const acceptInvitation = useAcceptInvitation()
const updateProfile = useUpdateWorkspaceProfile()

const nickname = ref('')
const avatarKey = ref('char2')
const acceptedWorkspaceId = ref<string | null>(null)
const loading = ref(false)
const selectedAvatarSrc = computed(() => {
  return AVATAR_OPTIONS.find((avatar) => avatar.key === avatarKey.value)?.src ?? AVATAR_OPTIONS[0]?.src ?? ''
})

async function accept() {
  if (!nickname.value.trim()) {
    toast.error('Nickname is required')
    return
  }
  loading.value = true
  try {
    const workspace = await acceptInvitation.mutateAsync(token.value)
    await updateProfile.mutateAsync({
      workspaceId: workspace.id,
      nickname: nickname.value.trim(),
      avatar_key: avatarKey.value,
    })
    acceptedWorkspaceId.value = workspace.id
    authStore.setWorkspace(workspace.id)
    toast.success('Invitation accepted')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to accept invite'
    toast.error(message)
  } finally {
    loading.value = false
  }
}

async function enterWorkspace() {
  if (!acceptedWorkspaceId.value) return
  await router.push('/office')
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center px-4">
    <section class="w-full max-w-xl rounded-3xl border border-white/10 bg-[#141414]/90 p-8 shadow-2xl shadow-black/40 backdrop-blur-xl">
      <h1 class="text-2xl font-bold text-white">Workspace Invitation</h1>
      <p class="mt-2 text-sm text-gray-400">
        Join
        <span class="font-semibold text-gray-300">{{ invitationQuery.data.value?.name ?? 'workspace' }}</span>
      </p>

      <div class="mt-5 space-y-3">
        <input v-model="nickname" class="rounded-2xl border border-white/10 bg-[#1e1e1e] px-4 py-3 text-white" placeholder="Your nickname in this workspace" />
        <div class="grid grid-cols-3 gap-2 md:grid-cols-5">
          <button
            v-for="avatar in AVATAR_OPTIONS"
            :key="avatar.key"
            class="rounded-2xl border p-1"
            :class="avatarKey === avatar.key ? 'border-gray-300' : 'border-white/10'"
            @click="avatarKey = avatar.key"
          >
            <div class="flex aspect-[3/4] items-center justify-center rounded-xl border border-white/10 bg-[#111111] p-1.5">
              <img :src="avatar.src" class="h-full w-full object-contain" />
            </div>
          </button>
        </div>
        <div class="rounded-2xl border border-white/10 bg-[#1b1b1b] p-3">
          <p class="mb-2 text-xs uppercase tracking-[0.14em] text-gray-400">Selected character</p>
          <div class="flex h-36 w-28 items-center justify-center rounded-xl border border-white/10 bg-[#111111] p-2">
            <img :src="selectedAvatarSrc" class="h-full w-full object-contain" />
          </div>
        </div>
      </div>

      <div class="mt-6 flex gap-2">
        <Button :disabled="loading || acceptedWorkspaceId !== null" @click="accept">
          {{ loading ? 'Joining...' : acceptedWorkspaceId ? 'Joined' : 'Accept invitation' }}
        </Button>
        <Button variant="outline" :disabled="!acceptedWorkspaceId" @click="enterWorkspace">Enter workspace</Button>
      </div>
    </section>
  </div>
</template>
