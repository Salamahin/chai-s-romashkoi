<script lang="ts">
  import { onMount } from 'svelte'
  import { exchangeToken } from './auth_service'

  interface Props {
    onauthenticated: () => void
  }

  const { onauthenticated }: Props = $props()

  let error: string | null = $state(null)

  onMount(async () => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    if (code !== null) {
      history.replaceState(null, '', window.location.pathname)
      try {
        await exchangeToken(code)
        onauthenticated()
      } catch (err) {
        error = err instanceof Error ? err.message : 'Token exchange failed'
      }
    }
  })

  function handleLogin(): void {
    const issuerUrl = import.meta.env.VITE_OAUTH_ISSUER_URL as string
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string
    const redirectUri = encodeURIComponent(window.location.origin + '/')
    const url = `${issuerUrl}/authorize?response_type=code&client_id=${clientId}&redirect_uri=${redirectUri}&scope=openid%20email&login_hint=e2e@example.com`
    window.location.assign(url)
  }
</script>

<div class="flex min-h-screen items-center justify-center bg-white px-4">
  <div class="w-full max-w-xs text-center">
    <button
      onclick={handleLogin}
      class="font-mono text-xs rounded border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50 active:bg-gray-100 transition-colors"
    >
      Login
    </button>

    {#if error}
      <p class="mt-4 font-mono text-xs text-red-500">{error}</p>
    {/if}
  </div>
</div>
