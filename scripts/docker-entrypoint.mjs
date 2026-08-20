import { spawn } from 'node:child_process'

function requireEnv(variable) {
  const value = process.env[variable]
  if (!value || value.trim().length === 0) {
    console.error(
      JSON.stringify({
        event: 'config_missing',
        variable,
        source: 'scripts/docker-entrypoint.mjs',
      }),
    )
    process.exit(1)
  }
}

requireEnv('DATABASE_URL')
requireEnv('AUTH_SECRET')

const child = spawn(process.execPath, ['server.js'], {
  stdio: 'inherit',
})

child.on('error', (error) => {
  console.error(
    JSON.stringify({
      event: 'docker_entrypoint_spawn_failed',
      message: error.message,
    }),
  )
  process.exit(1)
})

child.on('exit', (code, signal) => {
  if (signal) {
    process.exit(1)
  }
  process.exit(code ?? 1)
})
