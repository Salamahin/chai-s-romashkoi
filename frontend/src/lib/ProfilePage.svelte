<script lang="ts">
  import { onMount } from 'svelte'
  import ProfileEditor from './ProfileEditor.svelte'
  import type { ProfileEntry } from './ProfileEntryRow.svelte'
  import { getSessionToken, clearSession } from './auth_service'
  import { getProfile, saveProfile, getKnownTags } from './profile_service'
  import type { ProfileEntry as ApiEntry } from './profile_service'
  import RelationsPanel from './RelationsPanel.svelte'

  interface Props {
    onback: () => void
    onclearauth: () => void
  }

  const { onback, onclearauth }: Props = $props()

  type LoadState = 'loading' | 'ready' | 'error'

  let loadState: LoadState = $state('loading')
  let errorMessage: string = $state('')
  let entries: ProfileEntry[] = $state([])
  let knownTags: string[] = $state([])
  let saving = $state(false)
  let saveError: string = $state('')
  let saveSuccess = $state(false)
  let token: string | null = $state(null)

  function toUiEntry(e: ApiEntry): ProfileEntry {
    return { id: e.entry_id, tag: e.tag, text: e.text, updated_at: e.updated_at }
  }

  function toApiEntry(e: ProfileEntry): ApiEntry {
    return { entry_id: e.id, tag: e.tag, text: e.text, updated_at: e.updated_at }
  }

  onMount(async () => {
    const t = getSessionToken()
    if (!t) {
      clearSession()
      onclearauth()
      return
    }
    token = t
    try {
      const [snapshot, tags] = await Promise.all([getProfile(t), getKnownTags(t)])
      entries = snapshot.entries.map(toUiEntry)
      knownTags = tags
      loadState = 'ready'
    } catch (e) {
      errorMessage = e instanceof Error ? e.message : String(e)
      loadState = 'error'
    }
  })

  async function handleSave(): Promise<void> {
    saving = true
    saveError = ''
    saveSuccess = false
    const t = getSessionToken()
    if (!t) {
      clearSession()
      onclearauth()
      return
    }
    try {
      const snapshot = await saveProfile(t, { entries: entries.map(toApiEntry) })
      entries = snapshot.entries.map(toUiEntry)
      saveSuccess = true
      setTimeout(() => { saveSuccess = false }, 2000)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      if (msg.includes('401')) {
        clearSession()
        onclearauth()
        return
      }
      saveError = msg
    } finally {
      saving = false
    }
  }
</script>

<div class="min-h-screen bg-gray-50">
  <div class="mx-auto max-w-xl px-4 py-8">
    <div class="mb-6 flex items-center gap-4">
      <button
        type="button"
        onclick={onback}
        class="text-sm text-gray-500 hover:text-gray-800 transition-colors"
      >
        ← Back
      </button>
      <h1 class="text-xl font-semibold text-gray-800 tracking-tight">Profile</h1>
    </div>

    {#if loadState === 'loading'}
      <p class="text-sm text-gray-400">Loading…</p>

    {:else if loadState === 'error'}
      <p class="rounded border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-600">
        {errorMessage}
      </p>

    {:else}
      <div class="rounded-lg border border-gray-200 bg-white px-4 pb-4">
        <ProfileEditor {entries} {knownTags} onchange={(updated) => { entries = updated }} />
      </div>

      <div class="mt-4 flex items-center gap-3">
        <button
          type="button"
          onclick={handleSave}
          disabled={saving}
          class="rounded bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50 transition-colors"
        >
          {saving ? 'Saving…' : 'Save'}
        </button>

        {#if saveSuccess}
          <span class="text-sm text-green-600">Saved</span>
        {/if}

        {#if saveError}
          <span class="text-sm text-red-500">{saveError}</span>
        {/if}
      </div>

      {#if token !== null}
        <RelationsPanel sessionToken={token} {onclearauth} />
      {/if}
    {/if}
  </div>
</div>
