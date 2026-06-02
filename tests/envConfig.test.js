import assert from 'node:assert/strict'
import test from 'node:test'

import { resolveMigrationBaseUrl } from '../src/utils/localMigration.js'
import viteConfig, { resolveViteDevPort } from '../vite.config.js'

test('resolveMigrationBaseUrl 会读取前端 env 中的 API 地址，并在缺失时回退本地默认值', () => {
  assert.equal(
    resolveMigrationBaseUrl({ VITE_API_BASE_URL: 'http://127.0.0.1:9100/api/' }),
    'http://127.0.0.1:9100/api',
  )

  assert.equal(resolveMigrationBaseUrl({}), 'http://127.0.0.1:8000/api')
})

test('resolveViteDevPort 会读取 VITE_DEV_PORT 并在缺失时回退默认端口', () => {
  assert.equal(resolveViteDevPort({ VITE_DEV_PORT: '9320' }), 9320)
  assert.equal(resolveViteDevPort({ VITE_DEV_PORT: 'abc' }), 5173)
  assert.equal(resolveViteDevPort({}), 5173)
})

test('vite 配置会读取 VITE_DEV_PORT 统一前端 dev 端口', async () => {
  process.env.VITE_DEV_PORT = '9320'
  const config = await viteConfig({
    command: 'serve',
    mode: 'test',
  })
  delete process.env.VITE_DEV_PORT

  assert.equal(config.server.port, 9320)
})
