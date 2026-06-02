import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const DEFAULT_VITE_DEV_PORT = 5173

export function resolveViteDevPort(env = {}) {
  const rawPort = typeof env?.VITE_DEV_PORT === 'string' ? env.VITE_DEV_PORT.trim() : ''
  const parsedPort = Number.parseInt(rawPort, 10)

  // 端口配置允许通过 .env 覆盖，但仍保留 Vite 传统 5173 作为本地默认值。
  return Number.isInteger(parsedPort) && parsedPort > 0 ? parsedPort : DEFAULT_VITE_DEV_PORT
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    server: {
      port: resolveViteDevPort(env),
    },
  }
})
