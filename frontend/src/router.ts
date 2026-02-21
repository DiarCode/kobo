import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/core/stores/auth.store'
import { pinia } from '@/core/stores/pinia'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/workspace' },
    {
      path: '/auth',
      name: 'auth',
      component: () => import('@/modules/auth/pages/auth-page.vue'),
      meta: { scene: 'Auth' },
    },
    {
      path: '/invite/:token',
      name: 'invite',
      component: () => import('@/modules/workspace/pages/invite-page.vue'),
      meta: { scene: 'Invitation' },
    },
    {
      path: '/workspace',
      name: 'workspace',
      component: () => import('@/modules/workspace/pages/workspace-page.vue'),
      meta: { scene: 'Workspaces' },
    },
    {
      path: '/workspace/create',
      name: 'workspace-create',
      component: () => import('@/modules/workspace/pages/workspace-create-page.vue'),
      meta: { scene: 'Create Workspace' },
    },
    {
      path: '/office',
      name: 'office',
      component: () => import('@/modules/office/pages/office-page.vue'),
      meta: { scene: 'Workspace' },
    },
    {
      path: '/assistant',
      name: 'assistant',
      component: () => import('@/modules/assistant/pages/assistant-page.vue'),
      meta: { scene: 'Assistant' },
    },
    {
      path: '/tasks',
      name: 'tasks',
      component: () => import('@/modules/tasks/pages/tasks-page.vue'),
      meta: { scene: 'Tasks' },
    },
    {
      path: '/artifacts',
      name: 'artifacts',
      component: () => import('@/modules/artifacts/pages/artifacts-page.vue'),
      meta: { scene: 'Artifacts' },
    },
    {
      path: '/agents',
      name: 'agents',
      component: () => import('@/modules/agents/pages/agents-page.vue'),
      meta: { scene: 'Agents' },
    },
    {
      path: '/council',
      name: 'council',
      component: () => import('@/modules/council/pages/council-page.vue'),
      meta: { scene: 'Council' },
    },
    {
      path: '/integrations',
      name: 'integrations',
      component: () => import('@/modules/integrations/pages/integrations-page.vue'),
      meta: { scene: 'Integrations' },
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia)
  authStore.init()
  await authStore.hydrateSession()
  await authStore.validateWorkspaceSelection()

  const isAuthRoute = to.path.startsWith('/auth')
  if (!authStore.user && !isAuthRoute) {
    return `/auth?redirect=${encodeURIComponent(to.fullPath)}`
  }
  if (authStore.user && isAuthRoute) {
    const redirect = typeof to.query.redirect === 'string' ? to.query.redirect : null
    return redirect ?? (authStore.workspaceId ? '/office' : '/workspace')
  }
  if (authStore.user && !authStore.workspaceId && (to.path === '/office' || to.path === '/assistant')) {
    return '/workspace'
  }
  return true
})

export default router
