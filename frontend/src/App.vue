<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { Button } from '@/core/components/ui/button'
import { Toaster } from '@/core/components/ui/sonner'
import { useAuthStore } from '@/core/stores/auth.store'
import { applyPageTitle } from '@/core/utils/page-title'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
authStore.init()

const isOfficeRoute = computed(() => route.path.startsWith('/office'))
const showLogout = computed(() => !route.path.startsWith('/auth') && !isOfficeRoute.value && !!authStore.user)

async function logout() {
  await authStore.logout()
  await router.push('/auth')
}

watch(
  () => route.fullPath,
  () => {
    const scene = typeof route.meta.scene === 'string' ? route.meta.scene : 'Workspace'
    if (route.path.startsWith('/office')) {
      applyPageTitle(scene)
      return
    }
    applyPageTitle(scene)
  },
  { immediate: true },
)
</script>

<template>
  <main v-if="isOfficeRoute" class="h-screen w-screen">
    <router-view />
    <Toaster />
  </main>

  <main v-else class="relative min-h-screen overflow-hidden bg-black">
    <div class="absolute inset-0 bg-[radial-gradient(circle_at_15%_10%,rgba(255,255,255,0.08),transparent_35%),radial-gradient(circle_at_80%_15%,rgba(255,255,255,0.05),transparent_32%),radial-gradient(circle_at_30%_85%,rgba(255,255,255,0.06),transparent_42%)]"></div>
    <div class="absolute inset-0 bg-[linear-gradient(135deg,#050505_0%,#101010_55%,#080808_100%)] opacity-95"></div>

    <div v-if="showLogout" class="absolute right-6 top-6 z-20">
      <Button variant="outline" @click="logout">Logout</Button>
    </div>

    <div class="relative z-10">
      <router-view />
    </div>
    <Toaster />
  </main>
</template>
