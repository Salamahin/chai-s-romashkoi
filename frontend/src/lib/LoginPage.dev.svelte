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

<div class="flex min-h-screen items-center justify-center bg-gray-50 px-4">
  <div class="w-full max-w-sm rounded-lg border border-gray-200 bg-white px-8 py-10 text-center">
    <h1 class="mb-1 text-lg font-semibold text-gray-800 tracking-tight">Chai's Romashkoi</h1>
    <p class="mb-8 text-sm text-gray-400">Local development</p>

    <button
      onclick={handleLogin}
      class="w-full rounded border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 active:bg-gray-100 transition-colors"
    >
      Login as dev@local.dev
    </button>

    {#if error}
      <p class="mt-4 text-sm text-red-500">{error}</p>
    {/if}
  </div>
</div>
