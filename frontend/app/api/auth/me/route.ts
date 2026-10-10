import { forwardToBackend } from '@/lib/api/forward'

export async function GET(request: Request) {
  return forwardToBackend(request, '/api/auth/me')
}
