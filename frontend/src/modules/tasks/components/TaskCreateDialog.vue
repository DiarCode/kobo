<script setup lang="ts">
import { ref, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { Button } from '@/core/components/ui/button'

interface Props {
  open?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  open: false,
})

const emit = defineEmits<{
  'update:open': [value: boolean]
  submit: [data: { title: string; description: string; acceptanceCriteria: string[] }]
}>()

const title = ref('')
const description = ref('')
const acceptanceCriteria = ref('')

// Reset form when dialog opens
watch(() => props.open, (isOpen) => {
  if (isOpen) {
    title.value = ''
    description.value = ''
    acceptanceCriteria.value = ''
  }
})

function close() {
  emit('update:open', false)
}

function submit() {
  if (!title.value.trim()) return
  emit('submit', {
    title: title.value.trim(),
    description: description.value.trim(),
    acceptanceCriteria: acceptanceCriteria.value
      .split(';')
      .map(item => item.trim())
      .filter(Boolean),
  })
  title.value = ''
  description.value = ''
  acceptanceCriteria.value = ''
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center">
    <!-- Backdrop -->
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="close" />
    
    <!-- Dialog -->
    <div class="relative z-10 w-full max-w-lg rounded-2xl border border-white/10 bg-[#121212] p-6 shadow-2xl">
      <!-- Header -->
      <div class="flex items-center justify-between border-b border-white/10 pb-4">
        <h2 class="text-lg font-semibold text-white">Create New Task</h2>
        <button
          @click="close"
          class="rounded-lg p-1.5 text-gray-400 hover:bg-white/5 hover:text-white transition-colors"
        >
          <X class="h-5 w-5" />
        </button>
      </div>

      <!-- Form -->
      <div class="mt-4 space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-300 mb-1.5">Title *</label>
          <input
            v-model="title"
            type="text"
            placeholder="Enter task title..."
            class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-blue-500/50 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
            @keydown.ctrl.enter.prevent="submit"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-300 mb-1.5">Description</label>
          <textarea
            v-model="description"
            rows="3"
            placeholder="Describe the task..."
            class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-blue-500/50 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-300 mb-1.5">Acceptance Criteria</label>
          <input
            v-model="acceptanceCriteria"
            type="text"
            placeholder="Criteria separated by semicolons..."
            class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-blue-500/50 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
            @keydown.ctrl.enter.prevent="submit"
          />
          <p class="mt-1 text-xs text-gray-500">Separate multiple criteria with semicolons (;)</p>
        </div>
      </div>

      <!-- Footer -->
      <div class="mt-6 flex justify-end gap-3 border-t border-white/10 pt-4">
        <Button variant="outline" @click="close">Cancel</Button>
        <Button :disabled="!title.trim()" @click="submit">
          Create Task
        </Button>
      </div>
    </div>
  </div>
</template>
