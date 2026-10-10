import { forwardToBackend } from '@/lib/api/forward'

interface ProjectRouteContext {
  params: Promise<{ id: string }>
}

export async function GET(request: Request, { params }: ProjectRouteContext) {
  const { id } = await params
  return forwardToBackend(request, `/api/projects/${encodeURIComponent(id)}`)
}

export async function PATCH(request: Request, { params }: ProjectRouteContext) {
  const { id } = await params
  return forwardToBackend(request, `/api/projects/${encodeURIComponent(id)}`)
}

export async function DELETE(request: Request, { params }: ProjectRouteContext) {
  const { id } = await params
  return forwardToBackend(request, `/api/projects/${encodeURIComponent(id)}`)
}
