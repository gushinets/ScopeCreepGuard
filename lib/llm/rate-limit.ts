const WINDOW_MS = 60_000
const MAX_REQUESTS = 10

const requestTimestamps = new Map<string, number[]>()

export function allowAnalyze(userId: string, nowMs: number): boolean {
  const windowStart = nowMs - WINDOW_MS
  const recent = (requestTimestamps.get(userId) ?? []).filter((t) => t > windowStart)

  if (recent.length >= MAX_REQUESTS) {
    return false
  }

  recent.push(nowMs)
  requestTimestamps.set(userId, recent)
  return true
}
