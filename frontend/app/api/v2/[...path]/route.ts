import { forwardToBackend } from '@/lib/api/forward'

async function forward(request: Request) { return forwardToBackend(request) }
export const GET = forward
export const POST = forward
export const PUT = forward
export const PATCH = forward
export const DELETE = forward
