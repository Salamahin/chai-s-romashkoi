<script lang="ts">
  import { getSessionToken, clearSession } from './lib/auth_service'
  import LoginPage from './lib/LoginPage.svelte'
  import ChatPage from './lib/ChatPage.svelte'

  let authenticated = $state(getSessionToken() !== null)
</script>

{#if authenticated}
  <ChatPage onclearauth={() => { clearSession(); authenticated = false }} />
{:else}
  <LoginPage onauthenticated={() => { authenticated = true }} />
{/if}
