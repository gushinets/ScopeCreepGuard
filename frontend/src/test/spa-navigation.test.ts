import { expect, it } from 'vitest'
import { publicDestination, workspacePath } from '@/shared/config/navigation'

it('keeps intended destinations including draft/recovery query and hash', () => {
  expect(publicDestination('/history?draft=working&keep=yes#reply')).toBe('/history?draft=working&keep=yes#reply')
  for (const path of ['https://evil.test/', '//evil.test/', '/\\evil.test', '/login', '/register', 'javascript:alert(1)']) {
    expect(publicDestination(path)).toBe('/')
  }
})

it('maps page destinations without losing unrelated query parameters or legacy draft identity', () => {
  expect(workspacePath('history', '?draft=legacy&keep=yes', '#reply')).toBe('/history?draft=legacy&keep=yes#reply')
  expect(workspacePath('edit_project', '?draft=working', '', 'a/b')).toBe('/projects/a%2Fb/edit?draft=working')
  expect(workspacePath('check', '?draft=working')).toBe('/?draft=working')
})
