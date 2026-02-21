import { describe, expect, it } from 'vitest'

import { buildPageTitle } from '@/core/utils/page-title'

describe('buildPageTitle', () => {
  it('uses app + scene when workspace is absent', () => {
    expect(buildPageTitle('Auth')).toBe('KOBO · Auth')
  })

  it('uses app + workspace + scene when workspace exists', () => {
    expect(buildPageTitle('Tasks', 'Alpha Team')).toBe('KOBO · Alpha Team · Tasks')
  })
})
