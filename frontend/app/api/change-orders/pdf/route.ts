import { forwardToBackend } from '@/lib/api/forward'

export async function POST(request: Request) {
  const response = await forwardToBackend(request)
  response.headers.set('Cache-Control', 'private, no-store')
  return response
}
