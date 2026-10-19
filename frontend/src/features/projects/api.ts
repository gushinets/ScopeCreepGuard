import { apiJson } from '@/shared/api/client'
import type { Project } from '@/shared/api/models'

export type PersistentProject = Project & { archivedAt?: string | null }
export interface NewProjectInput {
  clientEmail?: string | null; endDate?: string | null; clientName?: string
  name: string; industry: Project['industry']; scope: string; startDate: string
  pricingModel: NonNullable<Project['pricingModel']>; currency: NonNullable<Project['currency']>
  hourlyRate: string; fixedPrice: string
}
export const projectsApi = {
  list: (archived = false) => apiJson<{ projects: PersistentProject[] }>(`/api/v2/projects${archived ? '?archived=true' : ''}`, { cache: 'no-store' }),
  remove: (id: string) => apiJson(`/api/v2/projects/${encodeURIComponent(id)}`, { method: 'DELETE' }),
}
