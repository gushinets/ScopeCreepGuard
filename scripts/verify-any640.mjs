import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const args = process.argv.slice(2)
if (args[0] !== '--suite' || !['contracts', 'frontend', 'containers', 'auth-gateway', 'generation-gateway'].includes(args[1]) ||
  args.slice(2).some((argument) => argument !== '--update-fixtures')) {
  console.error('Usage: node scripts/verify-any640.mjs --suite contracts|frontend|containers|auth-gateway|generation-gateway [--update-fixtures]')
  process.exit(2)
}
const root = fileURLToPath(new URL('../', import.meta.url))
const env = { ...process.env }
for (const name of Object.keys(env)) {
  if (/^(SCOPE_GUARD_|SCG_|PG)/.test(name) || ['DATABASE_URL', 'TEST_DATABASE_URL', 'AUTH_SECRET', 'OPENAI_API_KEY'].includes(name)) delete env[name]
}
env.DATABASE_URL = ''
env.SCOPE_GUARD_DATABASE_URL = ''
env.OPENAI_API_KEY = ''
const result = spawnSync('uv', ['run', '--no-sync', 'python',
  args[1] === 'containers' ? 'scripts/verify_any640_containers.py' : args[1] === 'auth-gateway' ? 'scripts/verify_any640_auth_gateway.py' : args[1] === 'generation-gateway' ? 'scripts/verify_any640_generation_gateway.py' : 'scripts/verify_any640.py',
  ...(['containers', 'auth-gateway', 'generation-gateway'].includes(args[1]) ? [] : ['--suite', args[1]]),
  ...(args.includes('--update-fixtures') ? ['--update-fixtures'] : [])], {
  cwd: `${root}backend`, env, stdio: 'inherit', windowsHide: true,
})
if (result.error) console.error('Could not start disposable compatibility harness')
process.exit(result.status ?? 1)
