export interface ProjectDetails {
  clientName: string
  clientEmail: string
  endDate: string
}

const empty = (): ProjectDetails => ({ clientName: '', clientEmail: '', endDate: '' })
const key = (userId: string, projectId: string) => `scg:project:${userId}:${projectId}`

export function readProjectDetails(userId: string, projectId: string): ProjectDetails {
  try {
    const raw = localStorage.getItem(key(userId, projectId))
    if (!raw) return empty()
    const value: unknown = JSON.parse(raw)
    if (!value || typeof value !== 'object' || Array.isArray(value)) return empty()
    const data = value as Record<string, unknown>
    return {
      clientName: typeof data.clientName === 'string' ? data.clientName : '',
      clientEmail: typeof data.clientEmail === 'string' ? data.clientEmail : '',
      endDate: typeof data.endDate === 'string' ? data.endDate : '',
    }
  } catch {
    return empty()
  }
}

export function writeProjectDetails(userId: string, projectId: string, details: ProjectDetails): void {
  try {
    localStorage.setItem(key(userId, projectId), JSON.stringify(details))
  } catch {
    // Browser storage is optional; project data is still saved on the server.
  }
}
