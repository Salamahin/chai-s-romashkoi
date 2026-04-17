<script lang="ts">
  import { getSessionToken, clearSession, isSessionStale, silentRefresh } from './lib/auth_service'
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
        () => { authState = 'authenticated' },
        () => { authState = 'unauthenticated' },
      )
    }
  })
</script>

{#if authState === 'authenticated'}
  <ChatPage onclearauth={() => { clearSession(); authState = 'unauthenticated' }} />
{:else if authState === 'refreshing'}
  <div class="flex h-screen items-center justify-center text-gray-400">Signing in…</div>
{:else}
  <LoginPage onauthenticated={() => { authState = 'authenticated' }} />
{/if}
