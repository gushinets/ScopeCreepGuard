import { spawnSync } from 'node:child_process'
import { resolve } from 'node:path'
import type { DraftProofClaims } from '@/lib/drafts/types'

export function pythonProof(action: 'issue' | 'verify', claims: DraftProofClaims, proof?: string) {
  const result = spawnSync('uv', ['run', '--no-sync', 'python', 'tests/proof_interop.py'], {
    cwd: resolve('../backend'), windowsHide: true, encoding: 'utf8',
    input: JSON.stringify({ action, claims, proof, secret: process.env.AUTH_SECRET, now: Math.floor(Date.now() / 1000) }),
  })
  if (result.status !== 0) throw new Error('Python proof compatibility driver failed')
  return result.stdout.trim()
}
