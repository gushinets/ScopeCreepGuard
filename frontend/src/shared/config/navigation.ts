export type View = 'check' | 'projects' | 'new_project' | 'edit_project' | 'history' | 'drafts'

/** Adopt pre-router application state without losing its data to router bookkeeping. */
export function adoptHistoryState() {
  const previous = window.history.state
  if (previous && typeof previous === 'object' && !('usr' in previous)) {
    const { idx: _index, key: _key, ...retained } = previous
    window.history.replaceState({ ...previous, usr: retained }, '')
  }
}

/** Only application destinations may be resumed after authentication. */
export function publicDestination(value: string | null | undefined): string {
  if (!value || !value.startsWith('/') || value.startsWith('//') || /[\\\r\n]/.test(value)) return '/'
  const url = new URL(value, 'https://same-origin.test')
  if (url.origin !== 'https://same-origin.test' || ['/login', '/register'].includes(url.pathname)) return '/'
  return `${url.pathname}${url.search}${url.hash}`
}

export function workspacePath(view: View, search = '', hash = '', projectId?: string | null) {
  const paths = { check: '/', projects: '/projects', new_project: '/projects/new',
    edit_project: projectId ? `/projects/${encodeURIComponent(projectId)}/edit` : '/projects',
    history: '/history', drafts: '/drafts' }
  return `${paths[view]}${search}${hash}`
}

export function pageView(pathname: string): View {
  if (pathname === '/projects/new') return 'new_project'
  if (/^\/projects\/[^/]+\/edit$/.test(pathname)) return 'edit_project'
  if (pathname === '/projects') return 'projects'
  if (pathname === '/history') return 'history'
  if (pathname === '/drafts') return 'drafts'
  return 'check'
}
