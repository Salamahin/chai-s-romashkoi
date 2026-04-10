import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig(({ mode }) => ({
  plugins: [svelte(), tailwindcss()],
  resolve: {
    alias: mode === 'development' ? [
      {
        find: /.*\/LoginPage\.svelte$/,
        replacement: path.resolve(__dirname, 'src/lib/LoginPage.dev.svelte'),
      },
      {
        find: /.*\/auth_service$/,
        replacement: path.resolve(__dirname, 'src/lib/auth_service.dev.ts'),
      },
    ] : [],
  },
}))
