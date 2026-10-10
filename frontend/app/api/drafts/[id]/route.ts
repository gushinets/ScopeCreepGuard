import { forwardToBackend } from '@/lib/api/forward'

interface Context { params: Promise<{ id: string }> }
export async function GET(request: Request, { params }: Context) {
  const { id } = await params
  const response = await forwardToBackend(request, `/api/drafts/${encodeURIComponent(id)}`)
  response.headers.set('Cache-Control', 'private, no-store')
  return response
}
export async function PUT(request: Request, { params }: Context) {
  const { id } = await params
  return forwardToBackend(request, `/api/drafts/${encodeURIComponent(id)}`)
}
