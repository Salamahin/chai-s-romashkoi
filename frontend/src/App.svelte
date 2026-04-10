<script lang="ts">
  import { getSessionToken, clearSession } from './lib/auth_service'
  import LoginPage from './lib/LoginPage.svelte'
  import AppPage from './lib/AppPage.svelte'

  let authenticated = $state(getSessionToken() !== null)
</script>

{#if authenticated}
  <AppPage onclearauth={() => { clearSession(); authenticated = false }} />
{:else}
  <LoginPage onauthenticated={() => { authenticated = true }} />
{/if}
