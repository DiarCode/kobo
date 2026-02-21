<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'
import { useRouter } from 'vue-router'
import {
  AlertCircle,
  Bot,
  FileText,
  Headset,
  Settings,
  SquareKanban,
  Users,
  X,
} from 'lucide-vue-next'
import { toast } from 'vue-sonner'

import workspaceBg from '@/core/assets/workspaces/1_office.png'
import { openWorkspacePresenceSocket, openWorkspaceSocket } from '@/core/api/ws'
import { Button } from '@/core/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/core/components/ui/dialog'
import { useAuthStore } from '@/core/stores/auth.store'
import {
  useAddTaskAttachment,
  useAddTaskComment,
  useCreateTaskSubtask,
  useCreateTask,
  useDeleteTaskSubtask,
  useRequestTaskAgentRevision,
  useTaskAgentTimeline,
  useTaskAttachments,
  useTaskComments,
  useTaskSubtasks,
  useTasks,
  useUpdateTaskSubtask,
  useUpdateTask,
} from '@/modules/tasks/composables/tasks.composable'
import { AVATAR_OPTIONS } from '@/modules/workspace/constants/avatar-options'
import {
  useAddWorkspaceTaskStatus,
  useAgentRoleTemplates,
  useCreateWorkspaceAgent,
  useDeleteWorkspaceAgent,
  useRefreshWorkspaceInvite,
  useRemoveWorkspaceMember,
  useRemoveWorkspaceTaskStatus,
  useUploadWorkspaceFile,
  useUpdateWorkspaceActionRequired,
  useUpdateWorkspaceAgent,
  useUpdateWorkspaceProfile,
  useUpdateWorkspaceTaskStatus,
  useUpdateWorkspaceSettings,
  useWorkspace,
  useWorkspaceActionsRequired,
  useWorkspaceAgents,
  useWorkspaceFiles,
  useWorkspaceInvite,
  useWorkspaceMembers,
  useWorkspaceProfile,
  useWorkspaceTaskStatuses,
} from '@/modules/workspace/composables/workspace.composable'
import { applyPageTitle } from '@/core/utils/page-title'

type PresenceStatus = 'offline' | 'online' | 'working' | 'idle'

interface PresenceParticipant {
  id: string
  kind: 'user' | 'agent'
  name: string
  status: PresenceStatus
  x: number
  y: number
  avatar_key: string
  role_key?: string
}

type PanelKey = 'tasks' | 'members' | 'agents' | 'files' | 'actions' | 'assistant' | 'settings'

const PANEL_LIST: Array<{ key: PanelKey; icon: typeof SquareKanban; title: string }> = [
  { key: 'tasks', icon: SquareKanban, title: 'Tasks' },
  { key: 'members', icon: Users, title: 'Members' },
  { key: 'agents', icon: Bot, title: 'Agents' },
  { key: 'files', icon: FileText, title: 'Files' },
  { key: 'actions', icon: AlertCircle, title: 'Actions required' },
  { key: 'assistant', icon: Headset, title: 'Assistant' },
  { key: 'settings', icon: Settings, title: 'Settings' },
]

const router = useRouter()
const queryClient = useQueryClient()
const authStore = useAuthStore()
authStore.init()

const workspaceId = computed(() => authStore.workspaceId)
const workspaceQuery = useWorkspace(workspaceId)
const membersQuery = useWorkspaceMembers(workspaceId)
const profileQuery = useWorkspaceProfile(workspaceId)
const agentsQuery = useWorkspaceAgents(workspaceId)
const inviteQuery = useWorkspaceInvite(workspaceId)
const statusesQuery = useWorkspaceTaskStatuses(workspaceId)
const filesQuery = useWorkspaceFiles(workspaceId)
const actionsQuery = useWorkspaceActionsRequired(workspaceId)
const tasksQuery = useTasks(workspaceId)
const selectedTaskId = ref<string | null>(null)
const taskTimelineQuery = useTaskAgentTimeline(selectedTaskId)
const taskCommentsQuery = useTaskComments(selectedTaskId)
const taskAttachmentsQuery = useTaskAttachments(selectedTaskId)
const taskSubtasksQuery = useTaskSubtasks(selectedTaskId)
const createTask = useCreateTask()
const updateTask = useUpdateTask()
const createSubtask = useCreateTaskSubtask()
const updateSubtask = useUpdateTaskSubtask()
const deleteSubtask = useDeleteTaskSubtask()
const requestAgentRevision = useRequestTaskAgentRevision()
const addTaskComment = useAddTaskComment()
const addTaskAttachment = useAddTaskAttachment()
const addStatus = useAddWorkspaceTaskStatus()
const removeStatus = useRemoveWorkspaceTaskStatus()
const updateStatus = useUpdateWorkspaceTaskStatus()
const uploadFile = useUploadWorkspaceFile()
const updateAction = useUpdateWorkspaceActionRequired()
const updateSettings = useUpdateWorkspaceSettings()
const updateProfile = useUpdateWorkspaceProfile()
const removeMember = useRemoveWorkspaceMember()
const updateAgent = useUpdateWorkspaceAgent()
const createAgent = useCreateWorkspaceAgent()
const deleteAgent = useDeleteWorkspaceAgent()
const agentRoleTemplatesQuery = useAgentRoleTemplates()
const refreshInvite = useRefreshWorkspaceInvite()

const modalOpen = ref(false)
const activePanel = ref<PanelKey>('tasks')
const createTaskDialogOpen = ref(false)
const manageStatusesDialogOpen = ref(false)
const createAgentDialogOpen = ref(false)
const editAgentDialogOpen = ref(false)
const deleteAgentDialogOpen = ref(false)
const editingAgentId = ref<string | null>(null)
const deletingAgentId = ref<string | null>(null)
const draggingTaskId = ref<string | null>(null)

const participantMap = ref<Record<string, PresenceParticipant>>({})
const localStatus = ref<PresenceStatus>('online')
let socket: WebSocket | null = null
let eventSocket: WebSocket | null = null
let randomMotionTimer: ReturnType<typeof setInterval> | null = null
let closedByUnmount = false
const accessErrorHandled = ref(false)

const statusFilter = ref('all')
const executorFilter = ref('all')
const newTaskTitle = ref('')
const newTaskDescription = ref('')
const newTaskChecklist = ref('')
const newTaskStatus = ref('todo')
const newTaskExecutor = ref('none')
const newStatusLabel = ref('')
const newStatusKey = ref('')

const newFileName = ref('')
const selectedFile = ref<File | null>(null)

const taskEditTitle = ref('')
const taskEditDescription = ref('')
const taskEditPriority = ref<'low' | 'medium' | 'high' | 'urgent'>('medium')
const taskEditStatus = ref('todo')
const taskEditExecutor = ref('none')
const taskEditChecklist = ref('')
const taskEditProofExempt = ref(false)
const newTaskComment = ref('')
const newAttachmentName = ref('')
const newAttachmentUrl = ref('')
const newAttachmentMimeType = ref('')
const newSubtaskTitle = ref('')
const newSubtaskDescription = ref('')
const newSubtaskExecutor = ref('none')
const revisionInstruction = ref('')

const settingsName = ref('')
const settingsDescription = ref('')
const profileNickname = ref('')
const profileAvatar = ref('char1')

const agentDrafts = ref<Record<string, {
  role_key?: string
  full_name: string
  tone: string
  character?: string
  system_prompt: string
  avatar_key: string
  status: PresenceStatus
}>>({})

const avatarByKey = computed(() => Object.fromEntries(AVATAR_OPTIONS.map((avatar) => [avatar.key, avatar.src])))

const participants = computed(() => Object.values(participantMap.value))
const localParticipantId = computed(() => (authStore.user ? `user:${authStore.user.id}` : null))
const selectedTask = computed(() => (tasksQuery.data.value ?? []).find((task) => task.id === selectedTaskId.value) ?? null)
const openActionsCount = computed(() => (actionsQuery.data.value ?? []).filter((item) => item.status === 'open').length)
const editingAgentDraft = computed(() => {
  if (!editingAgentId.value) return null
  return agentDrafts.value[editingAgentId.value] ?? null
})

const executorOptions = computed(() => {
  const members = (membersQuery.data.value ?? []).map((member) => ({
    id: `user:${member.user_id}`,
    label: member.nickname || member.username || member.user_id,
  }))
  const agents = (agentsQuery.data.value ?? []).map((agent) => ({
    id: `agent:${agent.role_key}`,
    label: `${agent.full_name} (AI)`,
  }))
  return [...members, ...agents]
})

const availableAgentRoles = computed(() => {
  const all = agentRoleTemplatesQuery.data.value?.roles ?? []
  const existing = new Set((agentsQuery.data.value ?? []).map((agent) => agent.role_key))
  return all.filter((role) => !existing.has(role.key))
})

const filteredTasks = computed(() => {
  const tasks = tasksQuery.data.value ?? []
  return tasks.filter((task) => {
    if (statusFilter.value !== 'all' && task.status !== statusFilter.value) return false
    if (executorFilter.value === 'all') return true
    if (executorFilter.value.startsWith('user:')) return task.assignee_user_id === executorFilter.value.replace('user:', '')
    if (executorFilter.value.startsWith('agent:')) return task.assignee_agent_role === executorFilter.value.replace('agent:', '')
    return true
  })
})

const tasksByStatus = computed(() => {
  const statuses = statusesQuery.data.value ?? []
  return statuses.map((status) => ({
    ...status,
    tasks: filteredTasks.value.filter((task) => task.status === status.key),
  }))
})

const stageLabelByKey: Record<string, string> = {
  router: 'Router',
  planner: 'Planner',
  retrieve: 'Retrieve',
  execute: 'Execute',
  critic: 'Critic',
  verifier: 'Verifier',
  approval_gate: 'Approval gate',
  committer: 'Committer',
}

function openPanel(panel: PanelKey) {
  if (panel === 'assistant') {
    void router.push('/assistant')
    return
  }
  activePanel.value = panel
  modalOpen.value = true
}

function closeModal() {
  modalOpen.value = false
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value))
}

function setParticipant(participant: PresenceParticipant) {
  participantMap.value = { ...participantMap.value, [participant.id]: participant }
}

function removeParticipant(participantId: string) {
  const next = { ...participantMap.value }
  delete next[participantId]
  participantMap.value = next
}

function broadcastMove(participant: PresenceParticipant) {
  if (!socket || socket.readyState !== WebSocket.OPEN) return
  if (participant.id !== localParticipantId.value) return
  socket.send(JSON.stringify({ type: 'presence.move', x: participant.x, y: participant.y, status: localStatus.value }))
}

function randomWalkParticipants() {
  const localId = localParticipantId.value
  participants.value.forEach((participant) => {
    if (participant.kind !== 'agent' && participant.id !== localId) {
      return
    }
    const dx = Math.random() * 4 - 2
    const dy = Math.random() * 4 - 2
    const moved: PresenceParticipant = {
      ...participant,
      x: clamp(participant.x + dx, 6, 94),
      y: clamp(participant.y + dy, 8, 92),
    }
    setParticipant(moved)
    broadcastMove(moved)
  })
}

function avatarSrc(key?: string | null): string {
  if (key && avatarByKey.value[key]) return avatarByKey.value[key]
  return AVATAR_OPTIONS[0]?.src ?? ''
}

function formatTimelineTime(iso: string) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString()
}

function stageLabel(stage: string) {
  return stageLabelByKey[stage] ?? stage
}

function getHttpStatus(error: unknown): number | null {
  const maybe = error as { response?: { status?: number } }
  const status = maybe.response?.status
  return typeof status === 'number' ? status : null
}

async function exitToWorkspaceList(message: string) {
  if (accessErrorHandled.value) return
  accessErrorHandled.value = true
  toast.error(message)
  authStore.setWorkspace(null)
  await router.replace('/workspace')
}

async function createTaskItem() {
  if (!workspaceId.value || !newTaskTitle.value.trim()) {
    toast.error('Task title is required')
    return
  }
  const payload: Record<string, unknown> = {
    workspace_id: workspaceId.value,
    title: newTaskTitle.value.trim(),
    description: newTaskDescription.value.trim(),
    acceptance_criteria: newTaskChecklist.value
      .split('\n')
      .map((item) => item.trim())
      .filter(Boolean),
    status: newTaskStatus.value,
  }
  if (newTaskExecutor.value.startsWith('user:')) {
    payload.assignee_user_id = newTaskExecutor.value.replace('user:', '')
  }
  if (newTaskExecutor.value.startsWith('agent:')) {
    payload.assignee_agent_role = newTaskExecutor.value.replace('agent:', '')
  }
  try {
    await createTask.mutateAsync(payload as never)
    newTaskTitle.value = ''
    newTaskDescription.value = ''
    newTaskChecklist.value = ''
    createTaskDialogOpen.value = false
    toast.success('Task created')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to create task'
    toast.error(message)
  }
}

async function moveTask(taskId: string, statusKey: string) {
  if (!workspaceId.value) return
  try {
    await updateTask.mutateAsync({ taskId, workspaceId: workspaceId.value, status: statusKey })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not move task'
    toast.error(message)
  }
}

function onTaskDragStart(taskId: string) {
  draggingTaskId.value = taskId
}

function onTaskDragEnd() {
  draggingTaskId.value = null
}

async function onDropTask(statusKey: string) {
  if (!draggingTaskId.value) return
  await moveTask(draggingTaskId.value, statusKey)
  draggingTaskId.value = null
}

function selectTask(taskId: string) {
  selectedTaskId.value = taskId
}

function executorValueForTask(task: { assignee_user_id: string | null; assignee_agent_role: string | null }) {
  if (task.assignee_user_id) return `user:${task.assignee_user_id}`
  if (task.assignee_agent_role) return `agent:${task.assignee_agent_role}`
  return 'none'
}

async function saveTaskDetails() {
  if (!workspaceId.value || !selectedTaskId.value) return

  const payload: {
    taskId: string
    workspaceId: string
    title: string
    description: string
    status: string
    priority: 'low' | 'medium' | 'high' | 'urgent'
    acceptance_criteria: string[]
    assignee_user_id: string | null
    assignee_agent_role: string | null
    proof_exempt: boolean
  } = {
    taskId: selectedTaskId.value,
    workspaceId: workspaceId.value,
    title: taskEditTitle.value.trim(),
    description: taskEditDescription.value.trim(),
    status: taskEditStatus.value,
    priority: taskEditPriority.value,
    acceptance_criteria: taskEditChecklist.value
      .split('\n')
      .map((item) => item.trim())
      .filter(Boolean),
    assignee_user_id: null,
    assignee_agent_role: null,
    proof_exempt: taskEditProofExempt.value,
  }
  if (taskEditExecutor.value.startsWith('user:')) {
    payload.assignee_user_id = taskEditExecutor.value.replace('user:', '')
  } else if (taskEditExecutor.value.startsWith('agent:')) {
    payload.assignee_agent_role = taskEditExecutor.value.replace('agent:', '')
  }

  try {
    await updateTask.mutateAsync(payload)
    toast.success('Task updated')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not update task'
    toast.error(message)
  }
}

async function addCommentToTask() {
  if (!selectedTaskId.value || !newTaskComment.value.trim()) return
  try {
    await addTaskComment.mutateAsync({ taskId: selectedTaskId.value, content: newTaskComment.value.trim() })
    newTaskComment.value = ''
    toast.success('Comment added')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not add comment'
    toast.error(message)
  }
}

async function addSubtaskToTask() {
  if (!selectedTaskId.value || !newSubtaskTitle.value.trim()) {
    toast.error('Subtask title is required')
    return
  }
  const payload: {
    taskId: string
    title: string
    description?: string
    assignee_user_id?: string
    assignee_agent_role?: string
  } = {
    taskId: selectedTaskId.value,
    title: newSubtaskTitle.value.trim(),
  }
  if (newSubtaskDescription.value.trim()) {
    payload.description = newSubtaskDescription.value.trim()
  }
  if (newSubtaskExecutor.value.startsWith('user:')) {
    payload.assignee_user_id = newSubtaskExecutor.value.replace('user:', '')
  } else if (newSubtaskExecutor.value.startsWith('agent:')) {
    payload.assignee_agent_role = newSubtaskExecutor.value.replace('agent:', '')
  }
  try {
    await createSubtask.mutateAsync(payload)
    newSubtaskTitle.value = ''
    newSubtaskDescription.value = ''
    newSubtaskExecutor.value = 'none'
    toast.success('Subtask added')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not add subtask'
    toast.error(message)
  }
}

function subtaskExecutorValue(subtask: { assignee_user_id: string | null; assignee_agent_role: string | null }) {
  if (subtask.assignee_user_id) return `user:${subtask.assignee_user_id}`
  if (subtask.assignee_agent_role) return `agent:${subtask.assignee_agent_role}`
  return 'none'
}

async function setSubtaskStatus(subtaskId: string, status: 'todo' | 'in_progress' | 'done') {
  if (!selectedTaskId.value) return
  try {
    await updateSubtask.mutateAsync({ taskId: selectedTaskId.value, subtaskId, status })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not update subtask'
    toast.error(message)
  }
}

async function assignSubtask(subtaskId: string, value: string) {
  if (!selectedTaskId.value) return
  try {
    if (value.startsWith('user:')) {
      await updateSubtask.mutateAsync({
        taskId: selectedTaskId.value,
        subtaskId,
        assignee_user_id: value.replace('user:', ''),
        assignee_agent_role: null,
      })
      return
    }
    if (value.startsWith('agent:')) {
      await updateSubtask.mutateAsync({
        taskId: selectedTaskId.value,
        subtaskId,
        assignee_user_id: null,
        assignee_agent_role: value.replace('agent:', ''),
      })
      return
    }
    await updateSubtask.mutateAsync({
      taskId: selectedTaskId.value,
      subtaskId,
      assignee_user_id: null,
      assignee_agent_role: null,
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not assign subtask'
    toast.error(message)
  }
}

async function removeSubtask(subtaskId: string) {
  if (!selectedTaskId.value) return
  try {
    await deleteSubtask.mutateAsync({ taskId: selectedTaskId.value, subtaskId })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not remove subtask'
    toast.error(message)
  }
}

async function requestRevision() {
  if (!selectedTaskId.value || !revisionInstruction.value.trim()) {
    toast.error('Add revision request first')
    return
  }
  try {
    await requestAgentRevision.mutateAsync({
      taskId: selectedTaskId.value,
      instruction: revisionInstruction.value.trim(),
      stakes_level: 'medium',
    })
    revisionInstruction.value = ''
    toast.success('Agent revision started')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not request revision'
    toast.error(message)
  }
}

async function addAttachmentToTask() {
  if (!selectedTaskId.value || !newAttachmentName.value.trim() || !newAttachmentUrl.value.trim()) return
  try {
    await addTaskAttachment.mutateAsync({
      taskId: selectedTaskId.value,
      file_name: newAttachmentName.value.trim(),
      url: newAttachmentUrl.value.trim(),
      mime_type: newAttachmentMimeType.value.trim() || undefined,
    })
    newAttachmentName.value = ''
    newAttachmentUrl.value = ''
    newAttachmentMimeType.value = ''
    toast.success('Attachment added')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not add attachment'
    toast.error(message)
  }
}

async function addTaskStatus() {
  if (!workspaceId.value || !newStatusLabel.value.trim()) {
    toast.error('Status label is required')
    return
  }
  const key = (newStatusKey.value || newStatusLabel.value).trim().toLowerCase().replace(/\s+/g, '_')
  try {
    await addStatus.mutateAsync({ workspaceId: workspaceId.value, label: newStatusLabel.value.trim(), key })
    newStatusLabel.value = ''
    newStatusKey.value = ''
    toast.success('Status added')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not add status'
    toast.error(message)
  }
}

async function removeTaskStatus(statusKey: string) {
  if (!workspaceId.value) return
  try {
    await removeStatus.mutateAsync({ workspaceId: workspaceId.value, statusKey })
    toast.success('Status removed')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not remove status'
    toast.error(message)
  }
}

async function updateTaskStatusLabel(statusKey: string, label: string) {
  if (!workspaceId.value || !label.trim()) return
  try {
    await updateStatus.mutateAsync({ workspaceId: workspaceId.value, statusKey, label: label.trim() })
    toast.success('Status updated')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not update status'
    toast.error(message)
  }
}

async function moveTaskStatus(statusKey: string, direction: 'up' | 'down') {
  if (!workspaceId.value) return
  const statuses = statusesQuery.data.value ?? []
  const index = statuses.findIndex((item) => item.key === statusKey)
  if (index < 0) return
  const nextIndex = direction === 'up' ? index - 1 : index + 1
  if (nextIndex < 0 || nextIndex >= statuses.length) return
  try {
    await updateStatus.mutateAsync({ workspaceId: workspaceId.value, statusKey, order: nextIndex })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not reorder statuses'
    toast.error(message)
  }
}

async function addWorkspaceFile() {
  if (!workspaceId.value || !selectedFile.value) {
    toast.error('Select a local file to upload')
    return
  }
  try {
    await uploadFile.mutateAsync({
      workspaceId: workspaceId.value,
      file: selectedFile.value,
    })
    selectedFile.value = null
    newFileName.value = ''
    toast.success('File added')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not add file'
    toast.error(message)
  }
}

async function setActionStatus(actionId: string, status: 'open' | 'acknowledged' | 'done') {
  if (!workspaceId.value) return
  try {
    await updateAction.mutateAsync({ workspaceId: workspaceId.value, actionId, status })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not update action'
    toast.error(message)
  }
}

function handleFileInput(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0] ?? null
  selectedFile.value = file
  newFileName.value = file?.name ?? ''
}

async function saveSettings() {
  if (!workspaceId.value) return
  try {
    await updateSettings.mutateAsync({
      workspaceId: workspaceId.value,
      name: settingsName.value.trim(),
      description: settingsDescription.value.trim(),
    })
    await updateProfile.mutateAsync({
      workspaceId: workspaceId.value,
      nickname: profileNickname.value.trim(),
      avatar_key: profileAvatar.value,
    })
    toast.success('Settings saved')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not save settings'
    toast.error(message)
  }
}

async function copyInviteLink() {
  const link = inviteQuery.data.value?.invite_url
  if (!link) return
  await navigator.clipboard.writeText(link)
  toast.success('Invite link copied')
}

async function rotateInviteLink() {
  if (!workspaceId.value) return
  try {
    await refreshInvite.mutateAsync(workspaceId.value)
    toast.success('Invite link refreshed')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not refresh invite link'
    toast.error(message)
  }
}

async function removeWorkspaceMember(memberUserId: string) {
  if (!workspaceId.value) return
  try {
    await removeMember.mutateAsync({ workspaceId: workspaceId.value, memberUserId })
    toast.success('Member removed')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not remove member'
    toast.error(message)
  }
}

async function saveAgent(agentId: string) {
  if (!workspaceId.value) return
  const draft = agentDrafts.value[agentId]
  if (!draft) return
  try {
    await updateAgent.mutateAsync({
      workspaceId: workspaceId.value,
      agentId,
      full_name: draft.full_name,
      tone: draft.tone,
      character: draft.character,
      system_prompt: draft.system_prompt,
      avatar_key: draft.avatar_key,
      status: draft.status,
    })
    toast.success('Agent updated')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not update agent'
    toast.error(message)
  }
}

function openCreateAgentDialog() {
  agentDrafts.value.__new = {
    role_key: '',
    full_name: '',
    tone: '',
    character: '',
    system_prompt: '',
    avatar_key: 'char1',
    status: 'online',
  }
  createAgentDialogOpen.value = true
}

function hydrateNewAgentFromRole(roleKey: string) {
  const draft = agentDrafts.value.__new
  if (!draft) return
  const template = (agentRoleTemplatesQuery.data.value?.roles ?? []).find((item) => item.key === roleKey)
  if (!template) return
  draft.full_name = draft.full_name || template.display_name
  draft.tone = draft.tone || template.tone
  draft.character = draft.character || template.character
  draft.system_prompt = draft.system_prompt || template.system_prompt
  draft.avatar_key = draft.avatar_key || template.avatar_key
}

function openEditAgentDialog(agentId: string) {
  editingAgentId.value = agentId
  editAgentDialogOpen.value = true
}

function openDeleteAgentDialog(agentId: string) {
  deletingAgentId.value = agentId
  deleteAgentDialogOpen.value = true
}

async function createAgentFromDraft() {
  if (!workspaceId.value) return
  const draft = agentDrafts.value.__new
  if (!draft || !draft.role_key) {
    toast.error('Select role for new agent')
    return
  }
  try {
    await createAgent.mutateAsync({
      workspaceId: workspaceId.value,
      role_key: draft.role_key,
      full_name: draft.full_name.trim() || undefined,
      tone: draft.tone.trim() || undefined,
      character: draft.character?.trim() || undefined,
      system_prompt: draft.system_prompt.trim() || undefined,
      avatar_key: draft.avatar_key,
      status: draft.status,
    })
    createAgentDialogOpen.value = false
    delete agentDrafts.value.__new
    toast.success('Agent created')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not create agent'
    toast.error(message)
  }
}

async function saveEditedAgent() {
  if (!editingAgentId.value) return
  await saveAgent(editingAgentId.value)
  editAgentDialogOpen.value = false
}

async function confirmDeleteAgent() {
  if (!workspaceId.value || !deletingAgentId.value) return
  try {
    await deleteAgent.mutateAsync({ workspaceId: workspaceId.value, agentId: deletingAgentId.value })
    deleteAgentDialogOpen.value = false
    deletingAgentId.value = null
    toast.success('Agent deleted')
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Could not delete agent'
    toast.error(message)
  }
}

onMounted(async () => {
  if (!workspaceId.value) {
    await router.push('/workspace')
    return
  }
  closedByUnmount = false

  socket = openWorkspacePresenceSocket(workspaceId.value, (message) => {
    const event = message as {
      type?: string
      participants?: PresenceParticipant[]
      participant?: PresenceParticipant
      participant_id?: string
    }
    if (event.type === 'presence.snapshot' && Array.isArray(event.participants)) {
      const next: Record<string, PresenceParticipant> = {}
      event.participants.forEach((participant) => {
        const key = participant.kind === 'agent' ? `agent:${participant.id}` : participant.id
        next[key] = { ...participant, id: key }
      })
      participantMap.value = next
    } else if (event.type === 'presence.joined' && event.participant) {
      setParticipant(event.participant)
    } else if (event.type === 'presence.updated' && event.participant) {
      setParticipant(event.participant)
    } else if (event.type === 'presence.left' && event.participant_id) {
      removeParticipant(event.participant_id)
    }
  })
  eventSocket = openWorkspaceSocket(workspaceId.value, (message) => {
    const event = message as { type?: string }
    if (!event.type) return
    if (event.type.startsWith('agent.run.')) {
      queryClient.invalidateQueries({ queryKey: ['task-agent-timeline'] })
      queryClient.invalidateQueries({ queryKey: ['agent-run-timeline'] })
      queryClient.invalidateQueries({ queryKey: ['agent-runs', workspaceId.value] })
    }
  })
  socket.onclose = (event) => {
    if (closedByUnmount) return
    if (event.code === 1008) {
      void exitToWorkspaceList('You no longer have access to this workspace')
    }
  }

  randomMotionTimer = setInterval(randomWalkParticipants, 2200)
})

onUnmounted(() => {
  closedByUnmount = true
  socket?.close()
  socket = null
  eventSocket?.close()
  eventSocket = null
  if (randomMotionTimer) {
    clearInterval(randomMotionTimer)
    randomMotionTimer = null
  }
})

watch(
  () => statusesQuery.data.value,
  (statuses) => {
    const firstStatus = statuses?.[0]
    if (firstStatus && !newTaskStatus.value) {
      newTaskStatus.value = firstStatus.key
    }
    if (firstStatus && !taskEditStatus.value) {
      taskEditStatus.value = firstStatus.key
    }
  },
  { immediate: true },
)

watch(
  () => selectedTask.value,
  (task) => {
    if (!task) return
    taskEditTitle.value = task.title
    taskEditDescription.value = task.description ?? ''
    taskEditPriority.value = task.priority
    taskEditStatus.value = task.status
    taskEditExecutor.value = executorValueForTask(task)
    taskEditChecklist.value = (task.acceptance_criteria ?? []).join('\n')
    taskEditProofExempt.value = task.proof_exempt
  },
  { immediate: true },
)

watch(
  () => tasksQuery.data.value,
  (tasks) => {
    if (!tasks || tasks.length === 0) {
      selectedTaskId.value = null
      return
    }
    const exists = tasks.some((task) => task.id === selectedTaskId.value)
    if (!exists) {
      selectedTaskId.value = tasks[0]?.id ?? null
    }
  },
  { immediate: true },
)

watch(
  () => workspaceQuery.data.value,
  (workspace) => {
    if (!workspace) return
    settingsName.value = workspace.name
    settingsDescription.value = workspace.description ?? ''
  },
  { immediate: true },
)

watch(
  () => profileQuery.data.value,
  (profile) => {
    if (!profile) return
    profileNickname.value = profile.nickname
    profileAvatar.value = profile.avatar_key
  },
  { immediate: true },
)

watch(
  () => agentsQuery.data.value,
  (agents) => {
    if (!agents) return
    agentDrafts.value = Object.fromEntries(
      agents.map((agent) => [
        agent.id,
        {
          role_key: agent.role_key,
          full_name: agent.full_name,
          tone: agent.tone,
          character: agent.character,
          system_prompt: agent.system_prompt,
          avatar_key: agent.avatar_key,
          status: agent.status,
        },
      ]),
    )
    const next = { ...participantMap.value }
    agents.forEach((agent, index) => {
      const id = `agent:${agent.id}`
      const existing = next[id]
      next[id] = {
        id,
        kind: 'agent',
        name: agent.full_name,
        status: agent.status,
        x: existing?.x ?? 22 + index * 8,
        y: existing?.y ?? 52,
        avatar_key: agent.avatar_key,
        role_key: agent.role_key,
      }
    })
    participantMap.value = next
  },
  { immediate: true },
)

watch(
  () => [workspaceQuery.data.value?.name, activePanel.value, modalOpen.value] as const,
  ([workspaceName, panel, isModalOpen]) => {
    const scene = isModalOpen ? (PANEL_LIST.find((item) => item.key === panel)?.title ?? 'Workspace') : 'Workspace'
    applyPageTitle(scene, workspaceName)
  },
  { immediate: true },
)

watch(
  () => [
    workspaceQuery.error.value,
    membersQuery.error.value,
    profileQuery.error.value,
    agentsQuery.error.value,
    inviteQuery.error.value,
    statusesQuery.error.value,
    filesQuery.error.value,
    actionsQuery.error.value,
    tasksQuery.error.value,
  ],
  (errors) => {
    const forbidden = errors.some((error) => {
      const status = getHttpStatus(error)
      return status === 403 || status === 404
    })
    if (forbidden) {
      void exitToWorkspaceList('Your workspace session is invalid. Please select a workspace again.')
    }
  },
)
</script>

<template>
  <section class="relative h-screen w-screen overflow-hidden">
    <img :src="workspaceBg" alt="workspace" class="absolute inset-0 h-full w-full object-cover" />

    <div class="absolute left-6 top-1/2 z-20 -translate-y-1/2">
      <div class="flex flex-col gap-3">
        <button
          v-for="panel in PANEL_LIST"
          :key="panel.key"
          class="relative rounded-full border p-3 shadow-xl transition"
          :class="modalOpen && activePanel === panel.key
            ? 'border-blue-500/70 bg-blue-500 text-white shadow-[0_14px_24px_-14px_rgba(59,130,246,0.95)]'
            : 'border-white/20 bg-black/45 text-gray-300 hover:bg-black/70'"
          :title="panel.title"
          @click="openPanel(panel.key)"
        >
          <component :is="panel.icon" class="h-5 w-5" />
          <span
            v-if="panel.key === 'actions' && openActionsCount > 0"
            class="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-red-500"
          />
        </button>
      </div>
    </div>

    <article
      v-for="participant in participants"
      :key="participant.id"
      class="absolute z-10 -translate-x-1/2 -translate-y-1/2 transition-all duration-[1800ms] ease-in-out"
      :style="{ left: `${participant.x}%`, top: `${participant.y}%` }"
    >
      <p class="mb-1 rounded-full bg-black/60 px-2 py-0.5 text-center text-[11px] font-semibold text-gray-200">
        {{ participant.name }} · {{ participant.status }}
      </p>
      <img
        :src="avatarSrc(participant.avatar_key)"
        class="h-36 w-24 object-contain object-center drop-shadow-[0_8px_14px_rgba(0,0,0,0.65)]"
      />
    </article>

    <transition name="fade">
      <div v-if="modalOpen" class="absolute inset-0 z-30 bg-black/70 p-[5vh_5vw]" @click.self="closeModal">
        <section class="h-[90vh] w-[90vw] rounded-3xl border border-white/15 bg-[#121212]/95 shadow-2xl backdrop-blur-2xl">
          <header class="flex items-center justify-between border-b border-white/10 px-6 py-4">
            <div>
              <p class="text-xs uppercase tracking-[0.18em] text-gray-300">Workspace</p>
              <h2 class="text-xl font-semibold text-white">
                {{ PANEL_LIST.find((panel) => panel.key === activePanel)?.title }}
              </h2>
            </div>
            <button class="rounded-xl border border-white/10 bg-[#242424] p-2 text-gray-200" @click="closeModal">
              <X class="h-5 w-5" />
            </button>
          </header>

          <div class="h-[calc(90vh-76px)] overflow-auto p-6">
            <section v-if="activePanel === 'tasks'" class="space-y-5">
              <div class="flex flex-wrap gap-2">
                <Button variant="outline" @click="createTaskDialogOpen = true">Create task</Button>
                <Button variant="outline" @click="manageStatusesDialogOpen = true">Manage statuses</Button>
              </div>

              <div class="grid gap-3 rounded-2xl border border-white/10 bg-[#1a1a1a] p-4 lg:grid-cols-2">
                <select v-model="statusFilter" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white">
                  <option value="all">All statuses</option>
                  <option v-for="status in statusesQuery.data.value ?? []" :key="status.key" :value="status.key">{{ status.label }}</option>
                </select>
                <select v-model="executorFilter" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white">
                  <option value="all">All executors</option>
                  <option v-for="executor in executorOptions" :key="executor.id" :value="executor.id">{{ executor.label }}</option>
                </select>
              </div>

              <div class="grid gap-3 xl:grid-cols-[2.8fr,1fr]">
                <div class="overflow-x-auto">
                  <div class="flex min-w-max gap-3 pb-2">
                  <article
                    v-for="status in tasksByStatus"
                    :key="status.key"
                    class="w-[320px] shrink-0 rounded-2xl border border-white/10 bg-[#181818] p-3"
                    @dragover.prevent
                    @drop.prevent="onDropTask(status.key)"
                  >
                    <div class="mb-2 flex items-center justify-between">
                      <p class="text-sm font-semibold text-gray-200">{{ status.label }}</p>
                    </div>
                    <div class="space-y-2">
                      <article
                        v-for="task in status.tasks"
                        :key="task.id"
                        class="cursor-pointer rounded-xl border p-3"
                        :class="selectedTaskId === task.id ? 'border-blue-500/70 bg-[#1f2530]' : 'border-white/10 bg-[#212121]'"
                        draggable="true"
                        @dragstart="onTaskDragStart(task.id)"
                        @dragend="onTaskDragEnd"
                        @click="selectTask(task.id)"
                      >
                        <p class="text-sm font-semibold text-white">{{ task.title }}</p>
                        <p class="mt-1 text-xs text-gray-400">{{ task.description || 'No description' }}</p>
                        <p class="mt-2 text-[11px] uppercase tracking-[0.12em] text-gray-500">Drag to move between statuses</p>
                      </article>
                    </div>
                  </article>
                  </div>
                </div>

                <aside class="rounded-2xl border border-white/10 bg-[#1a1a1a] p-4">
                  <template v-if="selectedTask">
                    <p class="mb-3 text-xs uppercase tracking-[0.16em] text-gray-400">Task details</p>
                    <div class="space-y-2">
                      <input v-model="taskEditTitle" class="w-full rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Task title" />
                      <textarea v-model="taskEditDescription" class="h-20 w-full rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Task description" />
                      <div class="grid grid-cols-2 gap-2">
                        <select v-model="taskEditStatus" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white">
                          <option v-for="status in statusesQuery.data.value ?? []" :key="status.key" :value="status.key">{{ status.label }}</option>
                        </select>
                        <select v-model="taskEditPriority" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white">
                          <option value="low">low</option>
                          <option value="medium">medium</option>
                          <option value="high">high</option>
                          <option value="urgent">urgent</option>
                        </select>
                      </div>
                      <select v-model="taskEditExecutor" class="w-full rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white">
                        <option value="none">No executor</option>
                        <option v-for="executor in executorOptions" :key="executor.id" :value="executor.id">{{ executor.label }}</option>
                      </select>
                      <textarea
                        v-model="taskEditChecklist"
                        class="h-20 w-full rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white"
                        placeholder="Acceptance checklist (one item per line)"
                      />
                      <label class="flex items-center gap-2 text-xs text-gray-300">
                        <input v-model="taskEditProofExempt" type="checkbox" />
                        Allow done without artifact (proof exemption)
                      </label>
                      <Button class="w-full" variant="outline" @click="saveTaskDetails">Save task</Button>
                    </div>

                    <div class="mt-4 space-y-2">
                      <p class="text-xs uppercase tracking-[0.16em] text-gray-400">Comments</p>
                      <div class="max-h-28 space-y-1 overflow-auto rounded-xl border border-white/10 bg-[#161616] p-2">
                        <p v-if="(taskCommentsQuery.data.value?.length ?? 0) === 0" class="text-xs text-gray-500">No comments yet</p>
                        <article v-for="comment in taskCommentsQuery.data.value ?? []" :key="comment.id" class="rounded-lg bg-white/5 p-2">
                          <p class="text-[11px] font-semibold text-gray-200">{{ comment.author_username }}</p>
                          <p class="text-xs text-gray-300">{{ comment.content }}</p>
                        </article>
                      </div>
                      <div class="flex gap-2">
                        <input v-model="newTaskComment" class="min-w-0 flex-1 rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Add comment" />
                        <Button variant="outline" @click="addCommentToTask">Post</Button>
                      </div>
                    </div>

                    <div class="mt-4 space-y-2">
                      <p class="text-xs uppercase tracking-[0.16em] text-gray-400">Attachments</p>
                      <div class="max-h-24 space-y-1 overflow-auto rounded-xl border border-white/10 bg-[#161616] p-2">
                        <p v-if="(taskAttachmentsQuery.data.value?.length ?? 0) === 0" class="text-xs text-gray-500">No attachments yet</p>
                        <a
                          v-for="attachment in taskAttachmentsQuery.data.value ?? []"
                          :key="attachment.id"
                          :href="attachment.url"
                          target="_blank"
                          class="block rounded-lg bg-white/5 p-2 text-xs text-gray-300 underline"
                        >
                          {{ attachment.file_name }}
                        </a>
                      </div>
                      <input v-model="newAttachmentName" class="w-full rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="File name" />
                      <input v-model="newAttachmentUrl" class="w-full rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="File URL" />
                      <input v-model="newAttachmentMimeType" class="w-full rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="MIME type (optional)" />
                      <Button class="w-full" variant="outline" @click="addAttachmentToTask">Attach</Button>
                    </div>

                    <div class="mt-4 space-y-2">
                      <p class="text-xs uppercase tracking-[0.16em] text-gray-400">Subtasks</p>
                      <div class="rounded-xl border border-white/10 bg-[#161616] p-2">
                        <div class="grid gap-2 md:grid-cols-[1.4fr,1fr]">
                          <input v-model="newSubtaskTitle" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Subtask title" />
                          <select v-model="newSubtaskExecutor" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white">
                            <option value="none">No executor</option>
                            <option v-for="executor in executorOptions" :key="executor.id" :value="executor.id">{{ executor.label }}</option>
                          </select>
                        </div>
                        <textarea v-model="newSubtaskDescription" class="mt-2 h-16 w-full rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Subtask description (optional)" />
                        <Button class="mt-2 w-full" variant="outline" @click="addSubtaskToTask">Add subtask</Button>
                        <div class="mt-2 max-h-40 space-y-2 overflow-auto">
                          <p v-if="taskSubtasksQuery.isLoading.value" class="text-xs text-gray-500">Loading subtasks...</p>
                          <article
                            v-for="subtask in taskSubtasksQuery.data.value ?? []"
                            :key="subtask.id"
                            class="rounded-lg border border-white/10 bg-[#1f1f1f] p-2"
                          >
                            <div class="flex items-center justify-between gap-2">
                              <p class="text-xs font-semibold text-gray-100">{{ subtask.title }}</p>
                              <Button size="sm" variant="outline" @click="removeSubtask(subtask.id)">Delete</Button>
                            </div>
                            <p class="text-[11px] text-gray-400">{{ subtask.description || 'No description' }}</p>
                            <div class="mt-2 grid gap-2 sm:grid-cols-2">
                              <select
                                class="rounded-lg border border-white/10 bg-[#242424] px-2 py-1 text-xs text-white"
                                :value="subtask.status"
                                @change="setSubtaskStatus(subtask.id, ($event.target as HTMLSelectElement).value as 'todo' | 'in_progress' | 'done')"
                              >
                                <option value="todo">todo</option>
                                <option value="in_progress">in_progress</option>
                                <option value="done">done</option>
                              </select>
                              <select
                                class="rounded-lg border border-white/10 bg-[#242424] px-2 py-1 text-xs text-white"
                                :value="subtaskExecutorValue(subtask)"
                                @change="assignSubtask(subtask.id, ($event.target as HTMLSelectElement).value)"
                              >
                                <option value="none">No executor</option>
                                <option v-for="executor in executorOptions" :key="`sub-${subtask.id}-${executor.id}`" :value="executor.id">{{ executor.label }}</option>
                              </select>
                            </div>
                          </article>
                        </div>
                      </div>
                    </div>

                    <div class="mt-4 space-y-2">
                      <p class="text-xs uppercase tracking-[0.16em] text-gray-400">AI revision request</p>
                      <textarea
                        v-model="revisionInstruction"
                        class="h-16 w-full rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white"
                        placeholder="Add review notes / fixes and request new AI revision run"
                      />
                      <Button class="w-full" variant="outline" @click="requestRevision">Request AI revision</Button>
                    </div>

                    <div class="mt-4 space-y-2">
                      <p class="text-xs uppercase tracking-[0.16em] text-gray-400">Agent Steps</p>
                      <div class="max-h-52 space-y-2 overflow-auto rounded-xl border border-white/10 bg-[#161616] p-2">
                        <p v-if="taskTimelineQuery.isLoading.value" class="text-xs text-gray-500">Loading timeline...</p>
                        <p v-else-if="(taskTimelineQuery.data.value?.length ?? 0) === 0" class="text-xs text-gray-500">
                          No agent steps for this task yet.
                        </p>
                        <article
                          v-for="step in taskTimelineQuery.data.value ?? []"
                          :key="step.id"
                          class="rounded-lg border border-white/10 bg-white/5 p-2"
                        >
                          <div class="flex items-center justify-between gap-2">
                            <p class="text-xs font-semibold text-gray-100">
                              {{ stageLabel(step.stage) }} · {{ step.agent_role }}
                            </p>
                            <span
                              class="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em]"
                              :class="step.status === 'running'
                                ? 'bg-blue-500/20 text-blue-300'
                                : step.status === 'failed'
                                  ? 'bg-gray-700 text-gray-200'
                                  : 'bg-gray-800 text-gray-300'"
                            >
                              {{ step.status }}
                            </span>
                          </div>
                          <p class="mt-1 text-xs text-gray-300">{{ step.summary }}</p>
                          <p class="mt-1 text-[10px] text-gray-500">{{ formatTimelineTime(step.created_at) }}</p>
                        </article>
                      </div>
                    </div>
                  </template>

                  <div v-else class="flex h-full items-center justify-center text-sm text-gray-500">
                    Select a task to manage details, comments, and attachments.
                  </div>
                </aside>
              </div>

              <Dialog v-model:open="createTaskDialogOpen">
                <DialogContent class="border-white/15 bg-[#121212] text-white">
                  <DialogHeader>
                    <DialogTitle>Create task</DialogTitle>
                  </DialogHeader>
                  <div class="grid gap-3">
                    <input v-model="newTaskTitle" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Task title" />
                    <input v-model="newTaskDescription" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Task description" />
                    <select v-model="newTaskStatus" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white">
                      <option v-for="status in statusesQuery.data.value ?? []" :key="status.key" :value="status.key">{{ status.label }}</option>
                    </select>
                    <select v-model="newTaskExecutor" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white">
                      <option value="none">No executor</option>
                      <option v-for="executor in executorOptions" :key="executor.id" :value="executor.id">{{ executor.label }}</option>
                    </select>
                    <textarea
                      v-model="newTaskChecklist"
                      class="h-20 rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white"
                      placeholder="Acceptance checklist (one item per line)"
                    />
                    <Button @click="createTaskItem">Create task</Button>
                  </div>
                </DialogContent>
              </Dialog>

              <Dialog v-model:open="manageStatusesDialogOpen">
                <DialogContent class="border-white/15 bg-[#121212] text-white">
                  <DialogHeader>
                    <DialogTitle>Manage statuses</DialogTitle>
                  </DialogHeader>
                  <div class="space-y-3">
                    <div class="flex gap-2">
                      <input v-model="newStatusLabel" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="New status label" />
                      <input v-model="newStatusKey" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="status_key" />
                      <Button variant="outline" @click="addTaskStatus">Add</Button>
                    </div>
                    <ul class="space-y-2">
                      <li
                        v-for="status in statusesQuery.data.value ?? []"
                        :key="status.key"
                        class="rounded-xl border border-white/10 bg-[#1b1b1b] px-3 py-2"
                      >
                        <div class="flex items-center gap-2">
                          <input
                            :value="status.label"
                            class="min-w-0 flex-1 rounded-lg border border-white/10 bg-[#242424] px-2 py-1 text-sm text-white"
                            @change="updateTaskStatusLabel(status.key, ($event.target as HTMLInputElement).value)"
                          />
                          <p class="text-xs text-gray-500">{{ status.key }}</p>
                          <Button variant="outline" size="sm" @click="moveTaskStatus(status.key, 'up')">↑</Button>
                          <Button variant="outline" size="sm" @click="moveTaskStatus(status.key, 'down')">↓</Button>
                          <Button
                            v-if="!status.is_default"
                            variant="outline"
                            size="sm"
                            @click="removeTaskStatus(status.key)"
                          >
                            Remove
                          </Button>
                        </div>
                      </li>
                    </ul>
                  </div>
                </DialogContent>
              </Dialog>
            </section>

            <section v-else-if="activePanel === 'members'" class="space-y-4">
              <div class="rounded-2xl border border-white/10 bg-[#1a1a1a] p-4">
                <p class="text-xs uppercase tracking-[0.16em] text-gray-400">Invite link</p>
                <div class="mt-2 flex gap-2">
                  <input :value="inviteQuery.data.value?.invite_url ?? ''" readonly class="flex-1 rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" />
                  <Button variant="outline" @click="copyInviteLink">Copy</Button>
                  <Button variant="outline" @click="rotateInviteLink">Refresh</Button>
                </div>
              </div>

              <ul class="space-y-2">
                <li
                  v-for="member in membersQuery.data.value ?? []"
                  :key="member.user_id"
                  class="flex items-center justify-between rounded-2xl border border-white/10 bg-[#1a1a1a] px-4 py-3"
                >
                  <div class="flex items-center gap-3">
                    <img
                      :src="avatarSrc(member.avatar_key)"
                      class="h-10 w-8 rounded-lg border border-white/20 bg-black/35 p-0.5 object-contain"
                    />
                    <div>
                      <p class="font-semibold text-white">{{ member.nickname || member.username }}</p>
                      <p class="text-xs text-gray-400">{{ member.role }}</p>
                    </div>
                  </div>
                  <Button
                    v-if="member.role !== 'owner'"
                    variant="outline"
                    @click="removeWorkspaceMember(member.user_id)"
                  >
                    Remove
                  </Button>
                </li>
              </ul>
            </section>

            <section v-else-if="activePanel === 'agents'" class="space-y-3">
              <div class="flex justify-end">
                <Button @click="openCreateAgentDialog">Create agent</Button>
              </div>
              <article
                v-for="agent in agentsQuery.data.value ?? []"
                :key="agent.id"
                class="rounded-2xl border border-white/10 bg-[#1a1a1a] p-4"
              >
                <div class="flex items-center justify-between gap-3">
                  <div class="flex items-center gap-3">
                    <div class="flex h-20 w-14 items-center justify-center rounded-lg bg-[#111111] p-1.5">
                      <img :src="avatarSrc(agent.avatar_key)" class="h-full w-full object-contain" />
                    </div>
                    <div>
                      <p class="font-semibold text-white">{{ agent.full_name }}</p>
                      <p class="text-xs uppercase tracking-[0.12em] text-gray-400">{{ agent.role_key }}</p>
                      <p class="text-xs text-gray-500">Status: {{ agent.status }}</p>
                    </div>
                  </div>
                  <div class="flex gap-2">
                    <Button variant="outline" @click="openEditAgentDialog(agent.id)">Edit</Button>
                    <Button variant="outline" @click="openDeleteAgentDialog(agent.id)">Delete</Button>
                  </div>
                </div>
              </article>

              <Dialog v-model:open="createAgentDialogOpen">
                <DialogContent class="border-white/15 bg-[#121212] text-white">
                  <DialogHeader>
                    <DialogTitle>Create agent</DialogTitle>
                  </DialogHeader>
                  <div v-if="agentDrafts.__new" class="grid gap-2">
                    <input v-model="agentDrafts.__new.full_name" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Full name" />
                    <select v-model="agentDrafts.__new.role_key" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" @change="hydrateNewAgentFromRole(agentDrafts.__new.role_key || '')">
                      <option value="">Select role</option>
                      <option v-for="role in availableAgentRoles" :key="role.key" :value="role.key">{{ role.title }} ({{ role.key }})</option>
                    </select>
                    <input v-model="agentDrafts.__new.tone" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Tone" />
                    <input v-model="agentDrafts.__new.character" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Character style" />
                    <textarea v-model="agentDrafts.__new.system_prompt" class="h-20 rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="System prompt" />
                    <select v-model="agentDrafts.__new.avatar_key" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white">
                      <option v-for="avatar in AVATAR_OPTIONS" :key="avatar.key" :value="avatar.key">{{ avatar.key }}</option>
                    </select>
                    <Button @click="createAgentFromDraft">Create</Button>
                  </div>
                </DialogContent>
              </Dialog>

              <Dialog v-model:open="editAgentDialogOpen">
                <DialogContent class="border-white/15 bg-[#121212] text-white">
                  <DialogHeader>
                    <DialogTitle>Edit agent</DialogTitle>
                  </DialogHeader>
                  <div v-if="editingAgentId && editingAgentDraft" class="grid gap-2">
                    <input v-model="editingAgentDraft.full_name" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Name" />
                    <input v-model="editingAgentDraft.tone" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Tone" />
                    <input v-model="editingAgentDraft.character" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Character" />
                    <textarea v-model="editingAgentDraft.system_prompt" class="h-20 rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" />
                    <select v-model="editingAgentDraft.avatar_key" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white">
                      <option v-for="avatar in AVATAR_OPTIONS" :key="avatar.key" :value="avatar.key">{{ avatar.key }}</option>
                    </select>
                    <select v-model="editingAgentDraft.status" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white">
                      <option value="online">online</option>
                      <option value="working">working</option>
                      <option value="idle">idle</option>
                      <option value="offline">offline</option>
                    </select>
                    <Button @click="saveEditedAgent">Save</Button>
                  </div>
                </DialogContent>
              </Dialog>

              <Dialog v-model:open="deleteAgentDialogOpen">
                <DialogContent class="border-white/15 bg-[#121212] text-white">
                  <DialogHeader>
                    <DialogTitle>Delete agent</DialogTitle>
                  </DialogHeader>
                  <p class="text-sm text-gray-300">This removes the agent from workspace roster and presence map.</p>
                  <Button @click="confirmDeleteAgent">Confirm delete</Button>
                </DialogContent>
              </Dialog>
            </section>

            <section v-else-if="activePanel === 'files'" class="space-y-4">
              <div class="grid gap-2 rounded-2xl border border-white/10 bg-[#1a1a1a] p-4 md:grid-cols-[2fr,1fr]">
                <div>
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt,.md"
                    class="w-full rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white file:mr-3 file:rounded-lg file:border-0 file:bg-white file:px-3 file:py-1 file:text-black"
                    @change="handleFileInput"
                  />
                  <p class="mt-2 text-xs text-gray-500">Accepted: PDF, DOCX, TXT, MD. Uploaded to MinIO and indexed for search/RAG.</p>
                </div>
                <Button class="h-full" @click="addWorkspaceFile">Upload</Button>
              </div>
              <ul class="space-y-2">
                <li
                  v-for="item in filesQuery.data.value ?? []"
                  :key="item.id"
                  class="rounded-2xl border border-white/10 bg-[#1a1a1a] px-4 py-3"
                >
                  <a :href="item.url" target="_blank" class="font-semibold text-gray-300 underline">{{ item.name }}</a>
                  <p class="text-xs text-gray-400">{{ item.type }}</p>
                </li>
              </ul>
            </section>

            <section v-else-if="activePanel === 'actions'" class="space-y-4">
              <p class="text-sm text-gray-400">Actions are generated by AI/runtime events when your attention is needed.</p>
              <ul class="space-y-2">
                <li
                  v-for="action in actionsQuery.data.value ?? []"
                  :key="action.id"
                  class="rounded-2xl border border-white/10 bg-[#1a1a1a] px-4 py-3"
                >
                  <div class="flex items-center justify-between">
                    <div>
                      <p class="font-semibold text-white">{{ action.title }}</p>
                      <p class="text-xs text-gray-400">{{ action.description }}</p>
                    </div>
                    <select
                      class="rounded-lg border border-white/10 bg-[#242424] px-2 py-1 text-xs text-white"
                      :value="action.status"
                      @change="setActionStatus(action.id, ($event.target as HTMLSelectElement).value as 'open' | 'acknowledged' | 'done')"
                    >
                      <option value="open">open</option>
                      <option value="acknowledged">acknowledged</option>
                      <option value="done">done</option>
                    </select>
                  </div>
                </li>
              </ul>
            </section>

            <section v-else class="space-y-4">
              <div class="rounded-2xl border border-white/10 bg-[#1a1a1a] p-4">
                <p class="mb-2 text-xs uppercase tracking-[0.16em] text-gray-400">Workspace</p>
                <div class="grid gap-2 md:grid-cols-2">
                  <input v-model="settingsName" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Workspace name" />
                  <input v-model="settingsDescription" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Workspace description" />
                </div>
              </div>
              <div class="rounded-2xl border border-white/10 bg-[#1a1a1a] p-4">
                <p class="mb-2 text-xs uppercase tracking-[0.16em] text-gray-400">My profile</p>
                <div class="grid gap-2 md:grid-cols-[1fr,2fr]">
                  <input v-model="profileNickname" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white" placeholder="Nickname" />
                  <select v-model="profileAvatar" class="rounded-xl border border-white/10 bg-[#242424] px-3 py-2 text-white">
                    <option v-for="avatar in AVATAR_OPTIONS" :key="avatar.key" :value="avatar.key">{{ avatar.key }}</option>
                  </select>
                </div>
                <div class="mt-3 flex items-center gap-3 rounded-xl border border-white/10 bg-[#242424] p-2">
                  <div class="flex h-24 w-16 items-center justify-center rounded-lg border border-white/10 bg-[#111111] p-1.5">
                    <img :src="avatarSrc(profileAvatar)" class="h-full w-full object-contain" />
                  </div>
                  <p class="text-xs text-gray-300">Your character preview</p>
                </div>
              </div>
              <Button @click="saveSettings">Save settings</Button>
            </section>
          </div>
        </section>
      </div>
    </transition>
  </section>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
