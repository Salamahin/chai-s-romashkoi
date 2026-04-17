<script lang="ts">
  import { getSessionToken, clearSession, isSessionStale, silentRefresh } from './lib/auth_service'
  import { prefetch, clearCache } from './lib/app_cache.svelte'
  import LoginPage from './lib/LoginPage.svelte'
  import ChatPage from './lib/ChatPage.svelte'

  type AuthState = 'authenticated' | 'unauthenticated' | 'refreshing'

  function initialAuthState(): AuthState {
    if (isSessionStale()) return 'refreshing'
    if (getSessionToken() !== null) return 'authenticated'
    return 'unauthenticated'
  }

  let authState = $state<AuthState>(initialAuthState())

  async function handleAuthenticated(): Promise<void> {
    const token = getSessionToken()
    if (token) await prefetch(token)
    authState = 'authenticated'
  }

  $effect(() => {
    if (authState === 'refreshing') {
      silentRefresh(
        handleAuthenticated,
        () => { authState = 'unauthenticated' },
      )
    }
  })
</script>

{#if authState === 'authenticated'}
  <ChatPage onclearauth={() => { clearSession(); clearCache(); authState = 'unauthenticated' }} />
{:else if authState === 'refreshing'}
  <div class="flex h-screen items-center justify-center text-gray-400">Signing in…</div>
{:else}
  <LoginPage onauthenticated={handleAuthenticated} />
{/if}
