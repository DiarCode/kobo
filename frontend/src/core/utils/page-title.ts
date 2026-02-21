export const APP_TITLE = 'KOBO'

export type SceneTitle =
  | 'Auth'
  | 'Invitation'
  | 'Workspaces'
  | 'Create Workspace'
  | 'Workspace'
  | 'Tasks'
  | 'Members'
  | 'Agents'
  | 'Files'
  | 'Actions required'
  | 'Settings'
  | 'Assistant'
  | 'Artifacts'
  | 'Council'
  | 'Integrations'

export function buildPageTitle(scene: string, workspaceName?: string | null): string {
  const cleanedScene = scene.trim() || 'Workspace'
  const cleanedWorkspace = workspaceName?.trim()
  if (cleanedWorkspace) {
    return `${APP_TITLE} · ${cleanedWorkspace} · ${cleanedScene}`
  }
  return `${APP_TITLE} · ${cleanedScene}`
}

export function applyPageTitle(scene: string, workspaceName?: string | null): void {
  if (typeof document === 'undefined') return
  document.title = buildPageTitle(scene, workspaceName)
}
