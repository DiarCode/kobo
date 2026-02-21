<script setup lang="ts">
import { computed, ref } from 'vue'
import { Plus, MessageSquare, MoreHorizontal } from 'lucide-vue-next'
import { toast } from 'vue-sonner'

import { Button } from '@/core/components/ui/button'
import { useAuthStore } from '@/core/stores/auth.store'
import {
  useCreateTask,
  useTasks,
  useUpdateTask,
} from '@/modules/tasks/composables/tasks.composable'
import TaskCreateDialog from '@/modules/tasks/components/TaskCreateDialog.vue'
import TaskDetailsDialog from '@/modules/tasks/components/TaskDetailsDialog.vue'

const authStore = useAuthStore()
authStore.init()

const workspaceId = computed(() => authStore.workspaceId)
const tasksQuery = useTasks(workspaceId)
const createTask = useCreateTask()
const updateTask = useUpdateTask()

// Dialogs
const showCreateDialog = ref(false)
const showDetailsDialog = ref(false)
const selectedTaskId = ref<string | null>(null)

const statuses = [
  { key: 'backlog', label: 'Backlog', color: 'text-gray-400', bgColor: 'bg-gray-500/10' },
  { key: 'todo', label: 'Todo', color: 'text-blue-400', bgColor: 'bg-blue-500/10' },
  { key: 'in_progress', label: 'In Progress', color: 'text-yellow-400', bgColor: 'bg-yellow-500/10' },
  { key: 'review', label: 'Review', color: 'text-purple-400', bgColor: 'bg-purple-500/10' },
  { key: 'done', label: 'Done', color: 'text-green-400', bgColor: 'bg-green-500/10' },
] as const

const tasksByStatus = computed(() => {
  const tasks = tasksQuery.data.value ?? []
  return statuses.map((status) => ({
    ...status,
    tasks: tasks.filter((task) => task.status === status.key),
  }))
})

async function handleCreateTask(data: { title: string; description: string; acceptanceCriteria: string[] }) {
  if (!workspaceId.value) {
    toast.error('Select workspace first')
    return
  }
  try {
    await createTask.mutateAsync({
      workspace_id: workspaceId.value,
      title: data.title,
      description: data.description,
      acceptance_criteria: data.acceptanceCriteria,
    })
    showCreateDialog.value = false
    toast.success('Task created')
  } catch {
    toast.error('Failed to create task')
  }
}

async function moveTask(
  taskId: string,
  status: 'backlog' | 'todo' | 'in_progress' | 'blocked' | 'review' | 'done' | 'canceled',
) {
  if (!workspaceId.value) return
  try {
    await updateTask.mutateAsync({ taskId, workspaceId: workspaceId.value, status })
    toast.success(`Moved to ${status.replace('_', ' ')}`)
  } catch {
    toast.error('Task update failed. Proof-of-work may be required.')
  }
}

function openTaskDetails(taskId: string) {
  selectedTaskId.value = taskId
  showDetailsDialog.value = true
}

function getPriorityColor(priority: string) {
  switch (priority) {
    case 'urgent': return 'text-red-400 bg-red-500/10'
    case 'high': return 'text-orange-400 bg-orange-500/10'
    case 'medium': return 'text-yellow-400 bg-yellow-500/10'
    case 'low': return 'text-gray-400 bg-gray-500/10'
    default: return 'text-gray-400 bg-gray-500/10'
  }
}
</script>

<template>
  <section class="min-h-screen bg-black text-white">
    <div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <!-- Header -->
      <header class="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p class="text-xs uppercase tracking-[0.16em] text-gray-400">Workspace</p>
          <h1 class="mt-1 text-2xl font-semibold">Tasks</h1>
        </div>
        <Button @click="showCreateDialog = true">
          <Plus class="mr-2 h-4 w-4" />
          New Task
        </Button>
      </header>

      <!-- Kanban Board -->
      <div class="grid gap-4 overflow-x-auto pb-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        <article
          v-for="column in tasksByStatus"
          :key="column.key"
          class="flex min-w-[280px] flex-col rounded-2xl border border-white/10 bg-[#121212]"
        >
          <!-- Column Header -->
          <div class="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <div class="flex items-center gap-2">
              <span class="h-2 w-2 rounded-full" :class="column.bgColor.replace('/10', '')" />
              <h3 class="text-sm font-semibold">{{ column.label }}</h3>
              <span class="text-xs text-gray-500">({{ column.tasks.length }})</span>
            </div>
          </div>

          <!-- Tasks -->
          <div class="flex-1 space-y-2 p-3">
            <button
              v-for="task in column.tasks"
              :key="task.id"
              class="w-full rounded-xl border border-white/5 bg-[#1a1a1a] p-3 text-left transition hover:border-white/20"
              @click="openTaskDetails(task.id)"
            >
              <div class="flex items-start justify-between gap-2">
                <h4 class="flex-1 text-sm font-medium text-gray-100">{{ task.title }}</h4>
                <span class="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium" :class="getPriorityColor(task.priority)">
                  {{ task.priority }}
                </span>
              </div>
              <p v-if="task.description" class="mt-2 line-clamp-2 text-xs text-gray-400">
                {{ task.description }}
              </p>

              <!-- Quick Actions -->
              <div class="mt-3 flex items-center justify-between">
                <div class="flex gap-1">
                  <button
                    v-for="status in statuses.filter(s => s.key !== task.status && s.key !== 'backlog')"
                    :key="`${task.id}-${status.key}`"
                    class="rounded px-2 py-1 text-[10px] transition hover:bg-white/5"
                    :class="status.color"
                    :title="`Move to ${status.label}`"
                    @click.stop="moveTask(task.id, status.key)"
                  >
                    {{ status.label.split(' ')[0] }}
                  </button>
                </div>
                <button
                  class="rounded p-1 text-gray-500 transition hover:text-gray-300"
                  title="View details"
                >
                  <MoreHorizontal class="h-3.5 w-3.5" />
                </button>
              </div>
            </button>

            <p v-if="column.tasks.length === 0" class="py-4 text-center text-sm text-gray-600">
              No tasks
            </p>
          </div>
        </article>
      </div>

      <!-- Empty State -->
      <div v-if="!tasksQuery.data.value?.length && !tasksQuery.isLoading.value"
           class="flex flex-col items-center justify-center py-20">
        <div class="mb-4 rounded-full bg-white/5 p-6">
          <MessageSquare class="h-10 w-10 text-gray-500" />
        </div>
        <h3 class="text-lg font-medium text-gray-300">No tasks yet</h3>
        <p class="mt-1 text-sm text-gray-500">Create your first task to get started</p>
        <Button class="mt-4" @click="showCreateDialog = true">
          <Plus class="mr-2 h-4 w-4" />
          Create Task
        </Button>
      </div>

      <!-- Loading State -->
      <div v-if="tasksQuery.isLoading.value" class="flex justify-center py-20">
        <div class="h-8 w-8 animate-spin rounded-full border-2 border-white/20 border-t-white" />
      </div>
    </div>

    <!-- Dialogs -->
    <TaskCreateDialog
      v-model:open="showCreateDialog"
      @submit="handleCreateTask"
    />
    <TaskDetailsDialog
      v-model:open="showDetailsDialog"
      v-model:task-id="selectedTaskId"
    />
  </section>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
