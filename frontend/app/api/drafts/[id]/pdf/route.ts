import { forwardToBackend } from '@/lib/api/forward'

export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const response = await forwardToBackend(request, `/api/drafts/${encodeURIComponent(id)}/pdf`)
  response.headers.set('Cache-Control', 'private, no-store')
  return response
}
