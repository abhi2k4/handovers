import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Read the repository-root .env (BACKEND_PORT, FRONTEND_PORT); process env wins.
  const env = { ...loadEnv(mode, '../..', ''), ...process.env }
  const backend = `http://127.0.0.1:${env.BACKEND_PORT ?? '8000'}`

  return {
    plugins: [react(), tailwindcss()],
    // Brand media lives in the repo-level assets/ folder (see AGENTS.md); served at the site root.
    publicDir: '../../assets/logos',
    server: {
      port: Number(env.FRONTEND_PORT ?? 5173),
      strictPort: true,
      // Same-origin API calls in dev: the browser calls /api/*, Vite forwards to FastAPI.
      proxy: {
        '/api': { target: backend, changeOrigin: true },
      },
    },
  }
})
