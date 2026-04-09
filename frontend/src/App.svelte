<script lang="ts">
  import { onMount } from 'svelte'

  let message: string | null = $state(null)
  let error: string | null = $state(null)

  const apiUrl = import.meta.env.VITE_API_URL as string

  onMount(async () => {
    try {
      const res = await fetch(apiUrl)
      const data = await res.json() as { message: string }
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
