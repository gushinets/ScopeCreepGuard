import { forwardToBackend } from '@/lib/api/forward'

export async function POST(request: Request) {
  return forwardToBackend(request, '/api/replies/regenerate')
}
