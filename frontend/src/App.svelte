<script lang="ts">
  import { getSessionToken, clearSession } from './lib/auth_service'
  import LoginPage from './lib/LoginPage.svelte'
  import ProfilePage from './lib/ProfilePage.svelte'

  let authenticated = $state(getSessionToken() !== null)
</script>

{#if authenticated}
  <ProfilePage onclearauth={() => { clearSession(); authenticated = false }} />
{:else}
  <LoginPage onauthenticated={() => { authenticated = true }} />
{/if}
