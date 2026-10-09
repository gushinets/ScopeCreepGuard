import { spawn } from 'node:child_process'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

export function serverLaunch(env) {
  const httpsProxy = typeof env.HTTPS_PROXY === 'string' ? env.HTTPS_PROXY.trim() : ''
  const httpProxy = typeof env.HTTP_PROXY === 'string' ? env.HTTP_PROXY.trim() : ''
  const hasProxy = httpsProxy.length > 0 || httpProxy.length > 0
  if (!hasProxy) {
    return { args: ['server.js'], env, proxyConfigured: false }
  }
  return {
    args: ['server.js'],
    env: { ...env, NODE_USE_ENV_PROXY: '1' },
    proxyConfigured: true,
  }
}

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

function isDirectRun() {
  const entry = process.argv[1]
  if (!entry) return false
  return import.meta.url === pathToFileURL(path.resolve(entry)).href
}

if (isDirectRun()) {
  requireEnv('DATABASE_URL')
  requireEnv('AUTH_SECRET')

  const launch = serverLaunch(process.env)
  console.log(
    JSON.stringify({
      event: 'server_launch',
      proxyConfigured: launch.proxyConfigured,
    }),
  )

  const child = spawn(process.execPath, launch.args, {
    env: launch.env,
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
}
