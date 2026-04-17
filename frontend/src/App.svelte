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

  $effect(() => {
    if (authState === 'refreshing') {
      silentRefresh(
        async () => {
          const token = getSessionToken()
          if (token) await prefetch(token)
          authState = 'authenticated'
        },
        () => { authState = 'unauthenticated' },
      )
    }
  })

  async function handleAuthenticated(): Promise<void> {
    const token = getSessionToken()
    if (token) await prefetch(token)
    authState = 'authenticated'
  }
</script>

{#if authState === 'authenticated'}
  <ChatPage onclearauth={() => { clearSession(); clearCache(); authState = 'unauthenticated' }} />
{:else if authState === 'refreshing'}
  <div class="flex h-screen items-center justify-center text-gray-400">Signing in…</div>
{:else}
  <LoginPage onauthenticated={handleAuthenticated} />
{/if}
