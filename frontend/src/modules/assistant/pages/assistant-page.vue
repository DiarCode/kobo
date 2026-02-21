<script setup lang="ts">
import { computed, onBeforeUnmount, ref, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { Room, RoomEvent } from 'livekit-client'
import { Bot, Mic, MicOff, PhoneOff, Send, Waves, Sparkles, Settings, ChevronDown, ChevronUp } from 'lucide-vue-next'
import { toast } from 'vue-sonner'

import { Button } from '@/core/components/ui/button'
import { useAuthStore } from '@/core/stores/auth.store'
import {
  useAssistantHistory,
  useAssistantVoiceToken,
  streamAssistantChat,
} from '@/modules/assistant/composables/assistant.composable'
import { useTasks } from '@/modules/tasks/composables/tasks.composable'

const router = useRouter()
const authStore = useAuthStore()
authStore.init()

const workspaceId = computed(() => authStore.workspaceId)
const historyQuery = useAssistantHistory(workspaceId)
const tasksQuery = useTasks(workspaceId)
const voiceTokenMutation = useAssistantVoiceToken()

const message = ref('')
const selectedTaskId = ref<string>('')
const includeHistory = ref(true)
const speakResponses = ref(true)
const sending = ref(false)

// Streaming state
const streamingResponse = ref('')
const isStreaming = ref(false)

// Voice state
const livekitRoom = shallowRef<Room | null>(null)
const voiceStatus = ref<'disconnected' | 'connecting' | 'connected'>('disconnected')
const micEnabled = ref(false)
const activeParticipants = ref<string[]>([])

// UI state
const showSettings = ref(false)

async function sendMessage() {
  if (!workspaceId.value || !message.value.trim() || sending.value) return
  const text = message.value.trim()
  message.value = ''
  sending.value = true
  isStreaming.value = true
  streamingResponse.value = ''

  try {
    for await (const event of streamAssistantChat({
      workspaceId: workspaceId.value,
      message: text,
      task_id: selectedTaskId.value || undefined,
      include_history: includeHistory.value,
    })) {
      if (event.type === 'token' && event.content) {
        streamingResponse.value += event.content
      } else if (event.type === 'complete') {
        if (speakResponses.value && typeof window !== 'undefined' && 'speechSynthesis' in window) {
          const utterance = new SpeechSynthesisUtterance(streamingResponse.value.slice(0, 400))
          utterance.rate = 1
          window.speechSynthesis.cancel()
          window.speechSynthesis.speak(utterance)
        }
      } else if (event.type === 'error') {
        toast.error(event.message || 'Streaming failed')
      }
    }
    await historyQuery.refetch()
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : 'Assistant request failed'
    toast.error(errorMsg)
  } finally {
    sending.value = false
    isStreaming.value = false
    streamingResponse.value = ''
  }
}

function updateParticipants(room: Room) {
  const names = Array.from(room.remoteParticipants.values()).map((participant) => participant.name || participant.identity)
  activeParticipants.value = names
}

async function connectVoice() {
  if (!workspaceId.value || voiceStatus.value !== 'disconnected') return
  voiceStatus.value = 'connecting'
  try {
    const token = await voiceTokenMutation.mutateAsync(workspaceId.value)
    const room = new Room({
      adaptiveStream: true,
      dynacast: true,
      audioCaptureDefaults: {
        autoGainControl: true,
        echoCancellation: true,
        noiseSuppression: true,
      },
    })
    room.on(RoomEvent.Connected, () => {
      voiceStatus.value = 'connected'
      updateParticipants(room)
    })
    room.on(RoomEvent.ParticipantConnected, () => updateParticipants(room))
    room.on(RoomEvent.ParticipantDisconnected, () => updateParticipants(room))
    room.on(RoomEvent.Disconnected, () => {
      voiceStatus.value = 'disconnected'
      micEnabled.value = false
      activeParticipants.value = []
    })
    await room.connect(token.livekit_url, token.token)

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      stream.getTracks().forEach(track => track.stop())
    } catch {
      toast.error('Microphone access denied. Please allow microphone access in your browser.')
    }

    await room.localParticipant.setMicrophoneEnabled(true)
    micEnabled.value = true
    livekitRoom.value = room
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : 'Could not connect voice room'
    toast.error(errorMsg)
    voiceStatus.value = 'disconnected'
    livekitRoom.value = null
  }
}

async function disconnectVoice() {
  if (!livekitRoom.value) return
  livekitRoom.value.disconnect()
  livekitRoom.value = null
  voiceStatus.value = 'disconnected'
  micEnabled.value = false
  activeParticipants.value = []
}

async function toggleMic() {
  if (!livekitRoom.value || voiceStatus.value !== 'connected') return
  const next = !micEnabled.value
  await livekitRoom.value.localParticipant.setMicrophoneEnabled(next)
  micEnabled.value = next
}

onBeforeUnmount(() => {
  if (livekitRoom.value) {
    livekitRoom.value.disconnect()
    livekitRoom.value = null
  }
})
</script>

<template>
  <section class="min-h-screen bg-black text-white">
    <div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <!-- Minimal Header -->
      <header class="mb-6 flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-semibold">AI Assistant</h1>
          <p class="text-sm text-gray-400">Workspace-aware AI assistant</p>
        </div>
        <div class="flex items-center gap-2">
          <Button variant="outline" size="sm" @click="router.push('/office')">
            Back to Workspace
          </Button>
        </div>
      </header>

      <!-- Main Content: Two Column Layout -->
      <div class="grid gap-6 lg:grid-cols-3">
        <!-- Chat Section (2/3 width) -->
        <div class="lg:col-span-2 space-y-4">
          <!-- Chat Messages -->
          <div class="rounded-2xl border border-white/10 bg-[#121212] p-4">
            <div class="mb-3 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <Bot class="h-4 w-4 text-blue-400" />
                <h2 class="font-semibold">Conversation</h2>
              </div>
            </div>

            <div class="h-[50vh] space-y-3 overflow-y-auto rounded-xl border border-white/10 bg-[#0d0d0d] p-4">
              <p v-if="historyQuery.isLoading.value" class="text-sm text-gray-500 text-center py-8">
                Loading conversation...
              </p>
              <article
                v-for="item in historyQuery.data.value ?? []"
                :key="item.id"
                class="rounded-xl px-4 py-2"
                :class="item.role === 'assistant' ? 'bg-blue-500/10 border border-blue-500/20' : 'bg-[#1a1a1a] border border-white/5'"
              >
                <p class="text-[10px] uppercase tracking-wider text-gray-500 mb-1">{{ item.role }}</p>
                <p class="text-sm text-gray-100 whitespace-pre-wrap">{{ item.content }}</p>
              </article>

              <!-- Streaming Response -->
              <article
                v-if="isStreaming"
                class="rounded-xl bg-blue-500/20 border border-blue-500/30 px-4 py-2"
              >
                <div class="flex items-center gap-2 mb-1">
                  <Sparkles class="h-3 w-3 text-blue-400 animate-pulse" />
                  <p class="text-[10px] uppercase tracking-wider text-blue-400">Assistant</p>
                </div>
                <p class="text-sm text-gray-100">{{ streamingResponse }}<span class="animate-pulse">▋</span></p>
              </article>
            </div>

            <!-- Input Area -->
            <div class="mt-4 space-y-3">
              <textarea
                v-model="message"
                rows="3"
                class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-gray-500 focus:border-blue-500/50 focus:outline-none focus:ring-1 focus:ring-blue-500/50 resize-none"
                placeholder="Ask anything about your workspace..."
                @keydown.ctrl.enter.prevent="sendMessage"
              />
              <div class="flex items-center justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  @click="showSettings = !showSettings"
                >
                  <Settings class="h-4 w-4 mr-2" />
                  Settings
                  <ChevronDown v-if="!showSettings" class="h-4 w-4 ml-2" />
                  <ChevronUp v-else class="h-4 w-4 ml-2" />
                </Button>
                <Button :disabled="sending || isStreaming || !message.trim()" @click="sendMessage">
                  <Send v-if="!sending && !isStreaming" class="h-4 w-4 mr-2" />
                  {{ sending || isStreaming ? 'Sending...' : 'Send' }}
                </Button>
              </div>

              <!-- Collapsible Settings -->
              <div v-if="showSettings" class="rounded-xl border border-white/10 bg-[#1a1a1a] p-4 space-y-3">
                <div>
                  <label class="text-xs text-gray-400 block mb-1.5">Focused Task</label>
                  <select v-model="selectedTaskId" class="w-full rounded-lg border border-white/10 bg-[#0d0d0d] px-3 py-2 text-sm">
                    <option value="">No focused task</option>
                    <option v-for="task in tasksQuery.data.value ?? []" :key="task.id" :value="task.id">{{ task.title }}</option>
                  </select>
                </div>
                <div class="flex items-center gap-4">
                  <label class="flex items-center gap-2 cursor-pointer">
                    <input v-model="includeHistory" type="checkbox" class="rounded border-white/10" />
                    <span class="text-sm text-gray-300">Include history</span>
                  </label>
                  <label class="flex items-center gap-2 cursor-pointer">
                    <input v-model="speakResponses" type="checkbox" class="rounded border-white/10" />
                    <span class="text-sm text-gray-300">Speak responses</span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Voice Panel (1/3 width) -->
        <div class="space-y-4">
          <!-- Voice Control Card -->
          <div class="rounded-2xl border border-white/10 bg-[#121212] p-4">
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center gap-2">
                <Waves class="h-4 w-4 text-purple-400" />
                <h2 class="font-semibold">Voice</h2>
              </div>
              <span
                class="text-xs px-2 py-1 rounded-full"
                :class="{
                  'bg-gray-500/20 text-gray-400': voiceStatus === 'disconnected',
                  'bg-yellow-500/20 text-yellow-400': voiceStatus === 'connecting',
                  'bg-green-500/20 text-green-400': voiceStatus === 'connected',
                }"
              >
                {{ voiceStatus }}
              </span>
            </div>

            <div class="space-y-2">
              <Button
                v-if="voiceStatus === 'disconnected'"
                class="w-full"
                @click="connectVoice"
              >
                <Waves class="h-4 w-4 mr-2" />
                Connect Voice
              </Button>
              <template v-else>
                <Button
                  variant="outline"
                  class="w-full"
                  :class="{ 'bg-red-500/10 border-red-500/30 text-red-400': !micEnabled }"
                  @click="toggleMic"
                >
                  <Mic v-if="micEnabled" class="h-4 w-4 mr-2" />
                  <MicOff v-else class="h-4 w-4 mr-2" />
                  {{ micEnabled ? 'Mute' : 'Unmute' }}
                </Button>
                <Button
                  variant="outline"
                  class="w-full"
                  @click="disconnectVoice"
                >
                  <PhoneOff class="h-4 w-4 mr-2" />
                  Disconnect
                </Button>
              </template>
            </div>

            <!-- Participants -->
            <div v-if="voiceStatus === 'connected'" class="mt-4 pt-4 border-t border-white/10">
              <p class="text-xs text-gray-400 mb-2">Participants</p>
              <div class="space-y-1">
                <p class="text-sm text-gray-300">You</p>
                <p v-for="participant in activeParticipants" :key="participant" class="text-sm text-gray-300">
                  {{ participant }}
                </p>
                <p v-if="activeParticipants.length === 0" class="text-xs text-gray-500">No other participants</p>
              </div>
            </div>
          </div>

          <!-- Info Card -->
          <div class="rounded-2xl border border-white/10 bg-[#121212] p-4">
            <h3 class="text-sm font-semibold mb-2">About</h3>
            <p class="text-xs text-gray-400 leading-relaxed">
              Your AI assistant has access to your workspace context including tasks, files, artifacts, and conversation history. Responses are grounded in your actual data.
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
