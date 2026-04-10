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

<div class="flex items-center justify-center h-screen bg-white">
  <div class="flex flex-col items-center gap-3">
    <button
      onclick={handleLogin}
      class="px-4 py-2 border border-gray-300 rounded text-sm text-gray-700 hover:bg-gray-50 active:bg-gray-100 transition-colors"
    >
      Login as dev@local.dev
    </button>
    {#if error}
      <p class="text-sm text-red-600">{error}</p>
    {/if}
  </div>
</div>
