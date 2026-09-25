import assert from 'node:assert/strict'
import test from 'node:test'
import { serverLaunch } from './docker-entrypoint.mjs'

test('starts the server directly when no proxy is configured', () => {
  const launch = serverLaunch({ HTTPS_PROXY: '  ', HTTP_PROXY: '' })
  assert.deepEqual(launch.args, ['server.js'])
  assert.equal(launch.proxyConfigured, false)
  assert.equal(launch.env.NODE_USE_ENV_PROXY, undefined)
})

test('enables Node env proxy when HTTPS_PROXY is set', () => {
  const launch = serverLaunch({
    HTTPS_PROXY: 'http://proxy.internal:8888',
    NODE_USE_ENV_PROXY: '',
    PATH: '/usr/bin',
  })
  assert.deepEqual(launch.args, ['server.js'])
  assert.equal(launch.proxyConfigured, true)
  assert.equal(launch.env.NODE_USE_ENV_PROXY, '1')
  assert.equal(launch.env.HTTPS_PROXY, 'http://proxy.internal:8888')
  assert.equal(launch.env.PATH, '/usr/bin')
})

test('enables Node env proxy when only HTTP_PROXY is set', () => {
  const launch = serverLaunch({ HTTP_PROXY: 'http://proxy.internal:8888' })
  assert.deepEqual(launch.args, ['server.js'])
  assert.equal(launch.proxyConfigured, true)
  assert.equal(launch.env.NODE_USE_ENV_PROXY, '1')
})
