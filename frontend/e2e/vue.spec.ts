import { test, expect } from '@playwright/test'

test('visits the app root url', async ({ page }) => {
  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({
      status: 401,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Unauthorized' }),
    })
  })

  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'KOBO' })).toBeVisible()
  await expect(page.getByText('Plan less. Ship with your AI team.')).toBeVisible()
  await expect(page).toHaveTitle('KOBO · Auth')
})

test('renders invite route and sets title', async ({ page }) => {
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith('/auth/me')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 'user-1', username: 'owner' }),
      })
      return
    }
    if (url.pathname.endsWith('/workspaces/invitations/tk-1')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'ws-1',
          name: 'Demo Workspace',
          slug: 'demo-workspace',
          description: 'demo',
          template: 'Custom',
          invite_token: 'tk-1',
          created_at: new Date().toISOString(),
        }),
      })
      return
    }
    await route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Not found' }),
    })
  })

  await page.goto('/invite/tk-1')
  await expect(page.getByRole('heading', { name: 'Workspace Invitation' })).toBeVisible()
  await expect(page).toHaveTitle('KOBO · Invitation')
})

test('updates office title by scene and shows task agent steps', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('kobo.workspace.user-1', 'ws-1')
  })

  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname

    if (path.endsWith('/auth/me')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 'user-1', username: 'owner' }),
      })
      return
    }
    if (path.endsWith('/workspaces/ws-1')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'ws-1',
          name: 'Demo Workspace',
          slug: 'demo-workspace',
          description: 'demo',
          template: 'Custom',
          invite_token: 'tk-1',
          created_at: new Date().toISOString(),
        }),
      })
      return
    }
    if (path.endsWith('/workspaces/ws-1/members')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
      return
    }
    if (path.endsWith('/workspaces/ws-1/me/profile')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          workspace_id: 'ws-1',
          user_id: 'user-1',
          nickname: 'Owner',
          avatar_key: 'char1',
          updated_at: new Date().toISOString(),
        }),
      })
      return
    }
    if (path.endsWith('/workspaces/ws-1/agents')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
      return
    }
    if (path.endsWith('/workspaces/ws-1/invite-link')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          workspace_id: 'ws-1',
          token: 'tk-1',
          invite_url: 'http://localhost:5173/invite/tk-1',
          created_at: new Date().toISOString(),
          revoked: false,
        }),
      })
      return
    }
    if (path.endsWith('/workspaces/ws-1/task-statuses')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { key: 'todo', label: 'To do', order: 0, is_default: true },
          { key: 'in_progress', label: 'In progress', order: 1, is_default: false },
        ]),
      })
      return
    }
    if (path.endsWith('/workspaces/ws-1/files') || path.endsWith('/workspaces/ws-1/actions-required')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
      return
    }
    if (path.endsWith('/tasks') && url.searchParams.get('workspace_id') === 'ws-1') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'task-1',
            workspace_id: 'ws-1',
            project_id: null,
            title: 'Implement timeline',
            description: 'Add structured stages',
            status: 'todo',
            priority: 'medium',
            acceptance_criteria: [],
            assignee_user_id: null,
            assignee_agent_role: null,
            proof_exempt: false,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ]),
      })
      return
    }
    if (path.endsWith('/tasks/task-1/comments') || path.endsWith('/tasks/task-1/attachments')) {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
      return
    }
    if (path.endsWith('/tasks/task-1/agent-timeline')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'step-1',
            run_id: 'run-1',
            task_id: 'task-1',
            workspace_id: 'ws-1',
            stage: 'planner',
            agent_role: 'project_manager',
            title: 'Planning',
            summary: 'Planned execution phases and checkpoints.',
            status: 'completed',
            created_at: new Date().toISOString(),
            metadata: {},
          },
        ]),
      })
      return
    }

    await route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({ detail: `Unhandled: ${path}` }),
    })
  })

  await page.goto('/office')
  await expect(page).toHaveTitle('KOBO · Demo Workspace · Workspace')
  await page.locator('button[title="Tasks"]').click()
  await expect(page).toHaveTitle('KOBO · Demo Workspace · Tasks')
  await expect(page.getByText('Agent Steps')).toBeVisible()
  await expect(page.getByText('Planned execution phases and checkpoints.')).toBeVisible()
})
