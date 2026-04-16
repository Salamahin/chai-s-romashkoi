<script lang="ts">
  import { exchangeToken } from './auth_service'

  interface Props {
    onauthenticated: () => void
  }

  const { onauthenticated }: Props = $props()

  let error: string | null = $state(null)

  async function handleLogin(): Promise<void> {
    error = null
    try {
      await exchangeToken('')
      onauthenticated()
    } catch (err) {
      error = err instanceof Error ? err.message : 'Dev login failed'
    }
  }
</script>

<div class="flex min-h-screen items-center justify-center bg-white px-4">
  <div class="w-full max-w-xs text-center">
    <img src="/logo.webp" alt="chai s romashkoi" class="mb-6 mx-auto w-32 h-32 object-contain" />
    <p class="mb-1 font-mono text-sm font-semibold text-gray-800">chai-s-romashkoi</p>
    <p class="mb-6 font-mono text-xs text-gray-400">local development</p>

    <button
      onclick={handleLogin}
      class="font-mono text-xs rounded border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50 active:bg-gray-100 transition-colors"
    >
      login as dev@local.dev
    </button>

    {#if error}
      <p class="mt-4 font-mono text-xs text-red-500">{error}</p>
    {/if}
  </div>
</div>
