<script lang="ts">
  import { onMount } from 'svelte'
  import { getSessionToken, clearSession } from './auth_service'
  import { getHomeData } from './home_service'
  import type { HomeData } from './home_service'
  import ProfilePage from './ProfilePage.svelte'

  interface Props {
    onclearauth: () => void
  }

  const { onclearauth }: Props = $props()

  type CurrentPage = 'home' | 'profile'

  let homeData: HomeData | null = $state(null)
  let loading = $state(true)
  let error: string | null = $state(null)
  let currentPage: CurrentPage = $state('home')

  onMount(async () => {
    const token = getSessionToken()
    if (!token) {
      clearSession()
      onclearauth()
      return
    }
    try {
      homeData = await getHomeData(token)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      if (msg.includes('401')) {
        clearSession()
        onclearauth()
        return
      }
      error = msg
    } finally {
      loading = false
    }
  })
</script>

{#if currentPage === 'profile'}
  <ProfilePage onback={() => { currentPage = 'home' }} {onclearauth} />
{:else}
  <div class="min-h-screen bg-gray-50">
    <div class="mx-auto max-w-xl px-4 py-8">
      {#if loading}
        <p class="text-sm text-gray-400">Loading…</p>
      {:else if error}
        <p class="rounded border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
      {:else if homeData}
        <p class="mb-8 text-sm text-gray-500">{homeData.message}</p>
        <button
          type="button"
          onclick={() => { currentPage = 'profile' }}
          class="relative rounded-lg border border-gray-200 bg-white px-6 py-4 text-left text-sm font-medium text-gray-800 hover:bg-gray-50 transition-colors"
        >
          Profile
          {#if homeData.pending_relations_count > 0}
            <span class="ml-2 inline-flex items-center justify-center rounded-full bg-red-500 px-2 py-0.5 text-xs font-semibold text-white">
              {homeData.pending_relations_count}
            </span>
          {/if}
        </button>
      {/if}
    </div>
  </div>
{/if}
