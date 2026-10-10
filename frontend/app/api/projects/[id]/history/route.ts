import { forwardToBackend } from '@/lib/api/forward'

interface Context { params: Promise<{ id: string }> }

export async function POST(request: Request, { params }: Context) {
  const { id } = await params
  return forwardToBackend(request, `/api/projects/${encodeURIComponent(id)}/history`)
}
