<script lang="ts">
  import { onMount } from 'svelte'
  import { clearSession } from './auth_service'
  import {
    listRelations,
    sendRelation,
    confirmRelation,
    deleteRelation,
    getKnownLabels,
  } from './relations_service'
  import type { RelationsSnapshot, RelationRecord } from './relations_service'
  import { cache, refreshRelations } from './app_cache.svelte'
  import RelationRow from './RelationRow.svelte'
  import LabelCombobox from './LabelCombobox.svelte'

  interface Props {
    sessionToken: string
    onclearauth: () => void
  }

  const { sessionToken, onclearauth }: Props = $props()

  let snapshot = $state<RelationsSnapshot | null>(null)
  let knownLabels: string[] = $state([])
  let loading = $state(true)
  let error: string | null = $state(null)
  let sendEmail = $state('')
  let sendLabel = $state('')
  let sending = $state(false)
  let sendError: string | null = $state(null)

  const allRelations: RelationRecord[] = $derived(snapshot === null ? [] : snapshot.relations)

  const pendingReceived: RelationRecord[] = $derived(
    allRelations.filter((r) => r.direction === 'received' && r.status === 'pending')
  )
  const pendingSent: RelationRecord[] = $derived(
    allRelations.filter((r) => r.direction === 'sent' && r.status === 'pending')
  )
  const confirmed: RelationRecord[] = $derived(
    allRelations.filter((r) => r.status === 'confirmed')
  )

  function handle401(e: unknown): boolean {
    const msg = e instanceof Error ? e.message : String(e)
    if (msg.includes('401')) {
      clearSession()
      onclearauth()
      return true
    }
    return false
  }

  function seedFromCache(): void {
    if (cache.relations !== null) {
      snapshot = cache.relations
      knownLabels = cache.knownLabels
    }
  }

  function backgroundRefresh(): void {
    void refreshRelations(sessionToken).then(() => {
      seedFromCache()
    })
  }

  async function loadData(): Promise<void> {
    loading = true
    error = null
    try {
      const [snap, labels] = await Promise.all([
        listRelations(sessionToken),
        getKnownLabels(sessionToken),
      ])
      snapshot = snap
      knownLabels = labels
    } catch (e) {
      if (!handle401(e)) {
        error = e instanceof Error ? e.message : String(e)
      }
    } finally {
      loading = false
    }
  }

  onMount(() => {
    if (cache.relations !== null) {
      // Cache hit — seed immediately, no spinner
      seedFromCache()
      loading = false
      // Background refresh — errors silently swallowed inside refreshRelations
      backgroundRefresh()
    } else {
      // Cache miss — fetch directly and surface errors
      void loadData()
    }
  })

  async function handleConfirm(relationId: string): Promise<void> {
    try {
      await confirmRelation(sessionToken, relationId)
    } catch (e) {
      if (!handle401(e)) {
        error = e instanceof Error ? e.message : String(e)
        return
      }
    }
    backgroundRefresh()
  }

  async function handleDelete(relationId: string): Promise<void> {
    try {
      await deleteRelation(sessionToken, relationId)
    } catch (e) {
      if (!handle401(e)) {
        error = e instanceof Error ? e.message : String(e)
        return
      }
    }
    backgroundRefresh()
  }

  async function handleSend(): Promise<void> {
    if (!sendEmail.trim() || !sendLabel.trim()) return
    sending = true
    sendError = null
    try {
      await sendRelation(sessionToken, sendEmail.trim(), sendLabel.trim())
      sendEmail = ''
      sendLabel = ''
    } catch (e) {
      if (!handle401(e)) {
        sendError = e instanceof Error ? e.message : String(e)
      }
      sending = false
      return
    }
    sending = false
    backgroundRefresh()
  }
</script>

<div class="mt-8">
  <h2 class="mb-4 text-base font-semibold text-gray-800 tracking-tight">Relations</h2>

  {#if loading}
    <p class="text-sm text-gray-400">Loading…</p>
  {:else if error}
    <p class="rounded border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
  {:else}
    {#if pendingReceived.length > 0}
      <div class="mb-4">
        <h3 class="mb-1 text-xs font-medium uppercase tracking-wide text-gray-400">Pending — received</h3>
        <div class="rounded-lg border border-gray-200 bg-white px-4 divide-y divide-gray-100">
          {#each pendingReceived as record (record.relation_id)}
            <RelationRow
              {record}
              onconfirm={() => handleConfirm(record.relation_id)}
              onreject={() => handleDelete(record.relation_id)}
              ondelete={null}
            />
          {/each}
        </div>
      </div>
    {/if}

    {#if pendingSent.length > 0}
      <div class="mb-4">
        <h3 class="mb-1 text-xs font-medium uppercase tracking-wide text-gray-400">Pending — sent</h3>
        <div class="rounded-lg border border-gray-200 bg-white px-4 divide-y divide-gray-100">
          {#each pendingSent as record (record.relation_id)}
            <RelationRow
              {record}
              onconfirm={null}
              onreject={null}
              ondelete={() => handleDelete(record.relation_id)}
            />
          {/each}
        </div>
      </div>
    {/if}

    {#if confirmed.length > 0}
      <div class="mb-4">
        <h3 class="mb-1 text-xs font-medium uppercase tracking-wide text-gray-400">Confirmed</h3>
        <div class="rounded-lg border border-gray-200 bg-white px-4 divide-y divide-gray-100">
          {#each confirmed as record (record.relation_id)}
            <RelationRow
              {record}
              onconfirm={null}
              onreject={null}
              ondelete={() => handleDelete(record.relation_id)}
            />
          {/each}
        </div>
      </div>
    {/if}

    <div class="rounded-lg border border-gray-200 bg-white px-4 py-4">
      <h3 class="mb-3 text-xs font-medium uppercase tracking-wide text-gray-400">Send relation request</h3>
      <div class="flex flex-col gap-2 sm:flex-row sm:items-start">
        <input
          type="email"
          bind:value={sendEmail}
          placeholder="Recipient email"
          class="flex-1 rounded border border-gray-200 px-3 py-2 text-sm text-gray-800 placeholder-gray-400 outline-none focus:border-gray-400 transition-colors"
        />
        <div class="w-full sm:w-40">
          <LabelCombobox
            value={sendLabel}
            options={knownLabels}
            onchange={(v) => { sendLabel = v }}
          />
        </div>
        <button
          type="button"
          onclick={handleSend}
          disabled={sending || !sendEmail.trim() || !sendLabel.trim()}
          class="rounded bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50 transition-colors"
        >
          {sending ? 'Sending…' : 'Send'}
        </button>
      </div>
      {#if sendError}
        <p class="mt-2 text-sm text-red-500">{sendError}</p>
      {/if}
    </div>
  {/if}
</div>
