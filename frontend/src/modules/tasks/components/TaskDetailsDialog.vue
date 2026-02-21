<script setup lang="ts">
import { computed, ref } from 'vue'
import { X, MessageSquare } from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import { Button } from '@/core/components/ui/button'
import { useAddTaskComment, useTaskComments } from '@/modules/tasks/composables/tasks.composable'

interface Props {
  open?: boolean
  taskId?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  open: false,
  taskId: null,
})

const emit = defineEmits<{
  'update:open': [value: boolean]
  'update:taskId': [value: string | null]
}>()

// Comments
const commentDraft = ref('')
const commentsQuery = useTaskComments(computed(() => props.taskId))
const addCommentMutation = useAddTaskComment()

async function submitComment() {
  if (!props.taskId || !commentDraft.value.trim()) return
  try {
    await addCommentMutation.mutateAsync({
      taskId: props.taskId,
      content: commentDraft.value.trim()
    })
    commentDraft.value = ''
    await commentsQuery.refetch()
    toast.success('Comment added')
  } catch {
    toast.error('Could not add comment')
  }
}

function close() {
  emit('update:open', false)
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <!-- Backdrop -->
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="close" />
    
    <!-- Dialog -->
    <div class="relative z-10 w-full max-w-2xl rounded-2xl border border-white/10 bg-[#121212] shadow-2xl flex flex-col max-h-[80vh]">
      <!-- Header -->
      <div class="flex items-center justify-between border-b border-white/10 p-6 shrink-0">
        <h2 class="text-lg font-semibold text-white">Task Details</h2>
        <button
          @click="close"
          class="rounded-lg p-1.5 text-gray-400 hover:bg-white/5 hover:text-white transition-colors"
        >
          <X class="h-5 w-5" />
        </button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6 space-y-6">
        <!-- Comments Section -->
        <div>
          <div class="flex items-center gap-2 mb-3">
            <MessageSquare class="h-4 w-4 text-blue-400" />
            <h3 class="text-sm font-semibold text-gray-300">Comments</h3>
          </div>
          
          <div class="space-y-2 mb-3 max-h-60 overflow-y-auto">
            <article
              v-for="comment in commentsQuery.data.value ?? []"
              :key="comment.id"
              class="rounded-xl border border-white/10 bg-[#1a1a1a] px-3 py-2"
            >
              <div class="flex items-center justify-between">
                <p class="text-xs font-semibold text-gray-300">{{ comment.author_username }}</p>
                <p class="text-[10px] text-gray-500">{{ new Date(comment.created_at).toLocaleString() }}</p>
              </div>
              <p class="mt-1 text-sm text-gray-200">{{ comment.content }}</p>
            </article>
            <p v-if="!commentsQuery.data.value?.length" class="text-sm text-gray-500 text-center py-4">
              No comments yet
            </p>
          </div>

          <div class="flex gap-2">
            <input
              v-model="commentDraft"
              type="text"
              placeholder="Write a comment..."
              class="flex-1 rounded-xl border border-white/10 bg-[#1a1a1a] px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-blue-500/50 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
              @keydown.ctrl.enter.prevent="submitComment"
            />
            <Button size="sm" :disabled="!commentDraft.trim()" @click="submitComment">
              Send
            </Button>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="border-t border-white/10 p-4 shrink-0">
        <Button variant="outline" class="w-full" @click="close">
          Close
        </Button>
      </div>
    </div>
  </div>
</template>
