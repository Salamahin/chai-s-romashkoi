<script lang="ts">
  import { getSessionToken, clearSession } from './lib/auth_service'
  import LoginPage from './lib/LoginPage.svelte'
  import HomePage from './lib/HomePage.svelte'

  let authenticated = $state(getSessionToken() !== null)
</script>

{#if authenticated}
  <HomePage onclearauth={() => { clearSession(); authenticated = false }} />
{:else}
  <LoginPage onauthenticated={() => { authenticated = true }} />
{/if}
