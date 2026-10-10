import { forwardToBackend } from '@/lib/api/forward'

export async function GET(request: Request) {
  const response = await forwardToBackend(request, '/api/drafts')
  response.headers.set('Cache-Control', 'private, no-store')
  return response
}
export async function POST(request: Request) {
  return forwardToBackend(request, '/api/drafts')
}
