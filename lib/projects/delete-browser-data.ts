/** Remove optional project details and obsolete browser records, never restore drafts. */
export function deleteProjectBrowserData(userId: string, projectId: string) {
  try {
    const prefixes = [
      `scg:change-order:${userId}:${projectId}:`,
      `scg:client-materials:${userId}:${projectId}:`,
    ]
    const keys = Array.from({ length: localStorage.length }, (_, i) => localStorage.key(i))
    for (const key of keys) {
      if (key && (key === `scg:project:${userId}:${projectId}` || prefixes.some(prefix => key.startsWith(prefix)))) localStorage.removeItem(key)
    }
    const active = `scg:client-materials:active:${userId}`
    if (JSON.parse(localStorage.getItem(active) ?? 'null')?.projectId === projectId) localStorage.removeItem(active)
  } catch { /* Browser storage is optional. */ }
}
