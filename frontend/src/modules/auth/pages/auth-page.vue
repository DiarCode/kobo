<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { Button } from '@/core/components/ui/button'
import { apiClient } from '@/core/api/http'
import { useAuthStore } from '@/core/stores/auth.store'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
authStore.init()

const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const loading = ref(false)

const redirectTarget = computed(() => {
  const redirect = route.query.redirect
  return typeof redirect === 'string' && redirect.length > 0 ? redirect : '/workspace'
})

async function submit() {
  if (!username.value.trim() || !password.value.trim()) {
    toast.error('Please fill username and password')
    return
  }

  loading.value = true
  try {
    const path = mode.value === 'register' ? 'auth/register' : 'auth/login'
    const response = await apiClient.post(path, { json: { username: username.value.trim(), password: password.value } }).json<{
      user: { id: string; username: string }
    }>()
    authStore.setUser({ id: response.user.id, username: response.user.username })
    toast.success(mode.value === 'register' ? 'Account created' : 'Logged in')
    await router.push(redirectTarget.value)
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Authentication failed'
    toast.error(message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center px-4">
    <section class="w-full max-w-md rounded-3xl border border-white/10 bg-[#141414]/85 p-8 shadow-2xl shadow-black/40 backdrop-blur-xl">
      <div class="mb-7 text-center">
        <div class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-white/20 bg-white text-lg font-bold text-black">
          K
        </div>
        <h1 class="text-2xl font-bold text-white">KOBO</h1>
        <p class="mt-2 text-sm text-gray-300">Plan less. Ship with your AI team.</p>
      </div>

      <div class="mb-4 grid grid-cols-2 gap-2 rounded-2xl bg-[#121212] p-1.5">
        <button
          class="rounded-xl py-2 text-sm font-semibold transition"
          :class="mode === 'login' ? 'bg-white text-gray-900' : 'text-gray-400'"
          @click="mode = 'login'"
        >
          Login
        </button>
        <button
          class="rounded-xl py-2 text-sm font-semibold transition"
          :class="mode === 'register' ? 'bg-white text-gray-900' : 'text-gray-400'"
          @click="mode = 'register'"
        >
          Register
        </button>
      </div>

      <form class="space-y-3" @submit.prevent="submit">
        <input
          v-model="username"
          autocomplete="username"
          class="w-full rounded-2xl border border-white/10 bg-[#1e1e1e] px-4 py-3 text-sm text-white placeholder:text-gray-500"
          placeholder="Username"
          required
        />
        <input
          v-model="password"
          type="password"
          minlength="8"
          autocomplete="current-password"
          class="w-full rounded-2xl border border-white/10 bg-[#1e1e1e] px-4 py-3 text-sm text-white placeholder:text-gray-500"
          placeholder="Password"
          required
        />

        <Button class="mt-2 w-full" size="lg" :disabled="loading" type="submit">
          {{ loading ? 'Please wait...' : mode === 'register' ? 'Create account' : 'Continue' }}
        </Button>
      </form>
    </section>
  </div>
</template>
