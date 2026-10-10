import { forwardToBackend } from '@/lib/api/forward'

export async function POST(request: Request) {
  return forwardToBackend(request, '/api/analyze')
}
