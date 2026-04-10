<script lang="ts">
  import { onMount } from 'svelte'
  import { getSessionToken, clearSession } from './auth_service'

  interface Props {
    onclearauth: () => void
  }

  const { onclearauth }: Props = $props()

  let message: string | null = $state(null)
  let error: string | null = $state(null)

  const apiUrl = import.meta.env.VITE_API_URL as string

  onMount(async () => {
    const token = getSessionToken()
    if (!token) {
      clearSession()
      onclearauth()
      return
    }
    try {
      const res = await fetch(apiUrl, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.status === 401) {
        clearSession()
        onclearauth()
        return
      }
      const data = (await res.json()) as { message: string }
      message = data.message
    } catch (e) {
      error = String(e)
    }
  })
</script>

<main>
  {#if error}
    <p>Error: {error}</p>
  {:else if message}
    <p>{message}</p>
  {:else}
    <p>Loading...</p>
  {/if}
</main>
