<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { Button } from '@/core/components/ui/button'
import { apiClient } from '@/core/api/http'
import { useAuthStore } from '@/core/stores/auth.store'
import { AVATAR_OPTIONS } from '@/modules/workspace/constants/avatar-options'
import {
  useAgentRoleTemplates,
  useBootstrapWorkspaceAgents,
  useCreateWorkspace,
  useUpdateWorkspaceProfile,
} from '@/modules/workspace/composables/workspace.composable'

type RoleConfig = {
  role_key: string
  full_name: string
  tone: string
  system_prompt: string
  avatar_key: string
  character: string
}

const router = useRouter()
const authStore = useAuthStore()
authStore.init()

const step = ref(1)
const loading = ref(false)
const workspaceId = ref<string | null>(null)
const inviteUrl = ref('')

const name = ref('')
const slug = ref('')
const description = ref('')
const nickname = ref('')
const selectedAvatar = ref('char1')
const roleConfigs = ref<RoleConfig[]>([])

const rolesQuery = useAgentRoleTemplates()
const createWorkspace = useCreateWorkspace()
const updateProfile = useUpdateWorkspaceProfile()
const bootstrapAgents = useBootstrapWorkspaceAgents()
const roleTemplates = computed(() => rolesQuery.data.value?.roles ?? [])

const stepTitle = computed(() => {
  if (step.value === 1) return 'Workspace details'
  if (step.value === 2) return 'Your workspace profile'
  if (step.value === 3) return 'Configure AI agents'
  return 'Invite your team'
})
const selectedAvatarSrc = computed(() => {
  return AVATAR_OPTIONS.find((avatar) => avatar.key === selectedAvatar.value)?.src ?? AVATAR_OPTIONS[0]?.src ?? ''
})

watch(
  () => name.value,
  (value) => {
    if (!slug.value) {
      slug.value = value.toLowerCase().trim().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')
    }
  },
)

function buildRoleConfig(roleKey: string): RoleConfig | null {
  const template = roleTemplates.value.find((role) => role.key === roleKey)
  if (!template) return null
  return {
    role_key: template.key,
    full_name: template.display_name,
    tone: template.tone,
    system_prompt: template.system_prompt,
    avatar_key: template.avatar_key,
    character: template.character,
  }
}

function availableRoleKeys(excludeCurrentRoleKey?: string) {
  const usedRoles = new Set(roleConfigs.value.map((role) => role.role_key))
  if (excludeCurrentRoleKey) {
    usedRoles.delete(excludeCurrentRoleKey)
  }
  return roleTemplates.value.filter((role) => !usedRoles.has(role.key))
}

function roleOptionsFor(roleKey: string) {
  return availableRoleKeys(roleKey)
}

function addAgentConfig() {
  const next = availableRoleKeys()[0]
  if (!next) {
    toast.error('All available roles were already added')
    return
  }
  const config = buildRoleConfig(next.key)
  if (!config) return
  roleConfigs.value.push(config)
}

function removeAgentConfig(index: number) {
  roleConfigs.value.splice(index, 1)
}

function applyRoleTemplate(index: number, roleKey: string) {
  const config = buildRoleConfig(roleKey)
  if (!config) return
  roleConfigs.value[index] = config
}

function avatarSrc(key: string) {
  return AVATAR_OPTIONS.find((avatar) => avatar.key === key)?.src ?? AVATAR_OPTIONS[0]?.src ?? ''
}

async function nextStep() {
  if (step.value === 1) {
    if (!name.value.trim() || !slug.value.trim()) {
      toast.error('Workspace name and slug are required')
      return
    }
  }
  if (step.value === 2) {
    if (!nickname.value.trim()) {
      toast.error('Nickname is required')
      return
    }
  }
  if (step.value < 4) {
    step.value += 1
    if (step.value === 4 && !workspaceId.value) {
      await completeSetup()
    }
  }
}

function prevStep() {
  if (step.value > 1) step.value -= 1
}

async function completeSetup() {
  if (workspaceId.value) return
  loading.value = true
  try {
    const created = await createWorkspace.mutateAsync({
      name: name.value.trim(),
      slug: slug.value.trim(),
      description: description.value.trim(),
      template: 'Custom',
    })
    workspaceId.value = created.id
    await updateProfile.mutateAsync({
      workspaceId: created.id,
      nickname: nickname.value.trim(),
      avatar_key: selectedAvatar.value,
    })
    await bootstrapAgents.mutateAsync({
      workspaceId: created.id,
      agents: roleConfigs.value.map((role) => ({
        role_key: role.role_key,
        full_name: role.full_name,
        tone: role.tone,
        system_prompt: role.system_prompt,
        avatar_key: role.avatar_key,
        character: role.character,
        status: 'online',
      })),
    })
    const invite = await apiClient.get(`workspaces/${created.id}/invite-link`).json<{ invite_url: string }>()
    inviteUrl.value = invite.invite_url
    authStore.setWorkspace(created.id)
    toast.success('Workspace created')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to complete workspace setup'
    toast.error(message)
  } finally {
    loading.value = false
  }
}

async function copyInvite() {
  if (!inviteUrl.value) return
  await navigator.clipboard.writeText(inviteUrl.value)
  toast.success('Invite link copied')
}

async function enterWorkspace() {
  if (workspaceId.value) {
    authStore.setWorkspace(workspaceId.value)
    await router.push('/office')
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center px-4">
    <section class="w-full max-w-4xl rounded-3xl border border-white/10 bg-[#141414]/90 p-8 shadow-2xl shadow-black/40 backdrop-blur-xl">
      <div class="mb-6 flex items-center justify-between">
        <div>
          <p class="text-xs uppercase tracking-[0.16em] text-gray-300">Create workspace</p>
          <h1 class="mt-1 text-2xl font-bold text-white">{{ stepTitle }}</h1>
        </div>
        <p class="rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-gray-300">Step {{ step }}/4</p>
      </div>

      <div v-if="step === 1" class="grid gap-3">
        <input v-model="name" class="rounded-2xl border border-white/10 bg-[#1e1e1e] px-4 py-3 text-white" placeholder="Workspace name" />
        <input v-model="slug" class="rounded-2xl border border-white/10 bg-[#1e1e1e] px-4 py-3 text-white" placeholder="workspace-slug" />
        <textarea v-model="description" class="h-28 rounded-2xl border border-white/10 bg-[#1e1e1e] px-4 py-3 text-white" placeholder="Description" />
      </div>

      <div v-else-if="step === 2" class="grid gap-4 lg:grid-cols-[1.1fr,1.9fr]">
        <div class="space-y-3">
          <input v-model="nickname" class="rounded-2xl border border-white/10 bg-[#1e1e1e] px-4 py-3 text-white" placeholder="Nickname in this workspace" />
          <div class="rounded-2xl border border-white/10 bg-[#1b1b1b] p-3">
            <p class="mb-2 text-xs uppercase tracking-[0.14em] text-gray-400">Selected character</p>
            <div class="flex h-36 w-28 items-center justify-center rounded-xl border border-white/10 bg-[#111111] p-2">
              <img :src="selectedAvatarSrc" class="h-full w-full object-contain" />
            </div>
          </div>
        </div>
        <div class="grid grid-cols-3 gap-2 md:grid-cols-5">
          <button
            v-for="avatar in AVATAR_OPTIONS"
            :key="avatar.key"
            class="rounded-2xl border p-1"
            :class="selectedAvatar === avatar.key ? 'border-gray-300' : 'border-white/10'"
            @click="selectedAvatar = avatar.key"
          >
            <div class="flex aspect-[3/4] items-center justify-center rounded-xl border border-white/10 bg-[#111111] p-1.5">
              <img :src="avatar.src" class="h-full w-full object-contain" />
            </div>
          </button>
        </div>
      </div>

      <div v-else-if="step === 3" class="space-y-3">
        <div class="flex items-center justify-between">
          <p class="text-sm text-gray-300">Add only the AI teammates you want. Roles are unique.</p>
          <Button
            variant="outline"
            :disabled="availableRoleKeys().length === 0 || rolesQuery.isLoading.value"
            @click="addAgentConfig"
          >
            Create agent
          </Button>
        </div>

        <div
          v-if="roleConfigs.length === 0"
          class="rounded-2xl border border-dashed border-white/20 bg-[#1b1b1b] p-8 text-center"
        >
          <p class="text-sm text-gray-300">No AI agents configured yet.</p>
          <p class="mt-1 text-xs text-gray-500">Click "Create agent" to append one.</p>
        </div>

        <article
          v-for="(role, index) in roleConfigs"
          :key="`${role.role_key}-${index}`"
          class="rounded-2xl border border-white/10 bg-[#1b1b1b] p-4"
        >
          <div class="mb-2 flex items-center justify-between gap-2">
            <select
              v-model="role.role_key"
              class="w-full rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-sm text-white"
              @change="applyRoleTemplate(index, role.role_key)"
            >
              <option
                v-for="roleOption in roleOptionsFor(role.role_key)"
                :key="roleOption.key"
                :value="roleOption.key"
              >
                {{ roleOption.title }}
              </option>
            </select>
            <Button variant="outline" @click="removeAgentConfig(index)">Remove</Button>
          </div>

          <div class="grid gap-2 md:grid-cols-2">
            <input v-model="role.full_name" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Agent name" />
            <input v-model="role.tone" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Tone" />
            <textarea v-model="role.system_prompt" class="md:col-span-2 h-20 rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="System prompt" />
            <select v-model="role.avatar_key" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white">
              <option v-for="avatar in AVATAR_OPTIONS" :key="avatar.key" :value="avatar.key">{{ avatar.key }}</option>
            </select>
            <input v-model="role.character" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Character style" />
          </div>
          <div class="mt-2">
            <div class="flex h-24 w-16 items-center justify-center rounded-xl border border-white/10 bg-[#111111] p-1.5">
              <img :src="avatarSrc(role.avatar_key)" class="h-full w-full object-contain" />
            </div>
          </div>
        </article>
      </div>

      <div v-else class="space-y-4">
        <p class="text-sm text-gray-300">Invite your team members to this workspace.</p>
        <div class="rounded-2xl border border-white/10 bg-[#1b1b1b] p-4">
          <p class="mb-2 text-xs uppercase tracking-[0.16em] text-gray-400">Invite link</p>
          <div class="flex flex-col gap-2 md:flex-row">
            <input :value="inviteUrl || 'Generate workspace first'" readonly class="flex-1 rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" />
            <Button variant="outline" :disabled="!inviteUrl" @click="copyInvite">Copy</Button>
          </div>
        </div>
        <div class="flex gap-2">
          <Button :disabled="loading || !!workspaceId" @click="completeSetup">
            {{ loading ? 'Creating...' : workspaceId ? 'Created' : 'Generate invite link' }}
          </Button>
          <Button variant="outline" :disabled="!workspaceId" @click="enterWorkspace">Enter workspace</Button>
        </div>
      </div>

      <div class="mt-6 flex items-center justify-between">
        <Button variant="outline" :disabled="step === 1 || loading" @click="prevStep">Back</Button>
        <Button v-if="step < 4" :disabled="loading" @click="nextStep">Next</Button>
      </div>
    </section>
  </div>
</template>
