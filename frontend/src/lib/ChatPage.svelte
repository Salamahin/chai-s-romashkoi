<script lang="ts">
  import { onMount } from 'svelte'
  import { getSessionToken, clearSession } from './auth_service'
  import { listEntries, createEntry, editEntry, deleteEntry } from './log_service'
  import { getHomeData } from './home_service'
  import { cache, refreshLog, currentWeekWindow } from './app_cache.svelte'
  import type { ChatMessage } from './chat_types'
  import ChatMessageList from './ChatMessageList.svelte'
  import ProfilePage from './ProfilePage.svelte'

  interface Props {
    onclearauth: () => void
  }

  const { onclearauth }: Props = $props()

  type CurrentPage = 'chat' | 'profile'

  let currentPage: CurrentPage = $state('chat')
  let messages: ChatMessage[] = $state([])
  let isLoadingMore = $state(false)
  let pendingCount = $state(0)
  let inputText = $state('')
  let isSending = $state(false)
  let loadError: string | null = $state(null)

  // Track the oldest week_start loaded so far for "load previous"
  let oldestWeekStart: Date | null = null

  function entryToMessage(entry: { entry_id: string; raw_text: string; logged_at: string; updated_at: string }): ChatMessage {
    return {
      localId: entry.entry_id,
      entry_id: entry.entry_id,
      raw_text: entry.raw_text,
      logged_at: entry.logged_at,
      updated_at: entry.updated_at,
      isEdited: entry.updated_at !== entry.logged_at,
      delivery: 'saved',
    }
  }

  function handleAuthError(msg: string): boolean {
    if (msg.includes('401')) {
      clearSession()
      onclearauth()
      return true
    }
    return false
  }

  onMount(async () => {
    const token = getSessionToken()
    if (!token) {
      clearSession()
      onclearauth()
      return
    }

    const { weekStart, weekEnd } = currentWeekWindow()
    oldestWeekStart = new Date(weekStart)

    if (cache.log !== null) {
      // Cache hit — seed immediately, then refresh in background (errors silently swallowed)
      messages = cache.log.entries.map(entryToMessage)
      if (cache.homeData !== null) {
        pendingCount = cache.homeData.pending_relations_count
      }
      void refreshLog(token).then(() => {
        if (cache.log !== null) {
          messages = cache.log.entries.map(entryToMessage)
        }
        if (cache.homeData !== null) {
          pendingCount = cache.homeData.pending_relations_count
        }
      })
    } else {
      // Cache miss (prefetch failed) — fetch directly and surface errors
      try {
        const [logResult, homeResult] = await Promise.allSettled([
          listEntries(token, weekStart, weekEnd),
          getHomeData(token),
        ])
        if (logResult.status === 'rejected') {
          const msg = logResult.reason instanceof Error ? logResult.reason.message : String(logResult.reason)
          if (handleAuthError(msg)) return
          loadError = msg
        } else {
          messages = logResult.value.entries.map(entryToMessage)
        }
        if (homeResult.status === 'fulfilled') {
          pendingCount = homeResult.value.pending_relations_count
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e)
        if (handleAuthError(msg)) return
        loadError = msg
      }
    }
  })

  async function handleSend(): Promise<void> {
    const text = inputText.trim()
    if (!text || isSending) return

    const token = getSessionToken()
    if (!token) { clearSession(); onclearauth(); return }

    const localId = crypto.randomUUID()
    const now = new Date().toISOString()
    const optimistic: ChatMessage = {
      localId,
      entry_id: null,
      raw_text: text,
      logged_at: now,
      updated_at: now,
      isEdited: false,
      delivery: 'pending',
    }

    messages = [...messages, optimistic]
    inputText = ''
    isSending = true

    try {
      const entry = await createEntry(token, text)
      messages = messages.map((m) =>
        m.localId === localId
          ? { ...m, entry_id: entry.entry_id, logged_at: entry.logged_at, updated_at: entry.updated_at, delivery: 'saved' }
          : m,
      )
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      if (handleAuthError(msg)) return
      messages = messages.map((m) =>
        m.localId === localId ? { ...m, delivery: 'failed' } : m,
      )
    } finally {
      isSending = false
    }
  }

  async function handleEdit(localId: string, newText: string): Promise<void> {
    const message = messages.find((m) => m.localId === localId)
    if (!message || !message.entry_id) return

    const token = getSessionToken()
    if (!token) { clearSession(); onclearauth(); return }

    try {
      const updated = await editEntry(token, message.entry_id, newText)
      messages = messages.map((m) =>
        m.localId === localId
          ? { ...m, raw_text: updated.raw_text, updated_at: updated.updated_at, isEdited: true }
          : m,
      )
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      if (handleAuthError(msg)) return
      // Edit failed — no rollback needed, row manages local editing state
    }
  }

  async function handleDelete(localId: string): Promise<void> {
    const message = messages.find((m) => m.localId === localId)
    if (!message || !message.entry_id) return

    const token = getSessionToken()
    if (!token) { clearSession(); onclearauth(); return }

    try {
      await deleteEntry(token, message.entry_id)
      messages = messages.filter((m) => m.localId !== localId)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      if (handleAuthError(msg)) return
    }
  }

  async function handleRetry(localId: string): Promise<void> {
    const message = messages.find((m) => m.localId === localId)
    if (!message) return

    const token = getSessionToken()
    if (!token) { clearSession(); onclearauth(); return }

    messages = messages.map((m) =>
      m.localId === localId ? { ...m, delivery: 'pending' } : m,
    )

    try {
      const entry = await createEntry(token, message.raw_text)
      messages = messages.map((m) =>
        m.localId === localId
          ? { ...m, entry_id: entry.entry_id, logged_at: entry.logged_at, updated_at: entry.updated_at, delivery: 'saved' }
          : m,
      )
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      if (handleAuthError(msg)) return
      messages = messages.map((m) =>
        m.localId === localId ? { ...m, delivery: 'failed' } : m,
      )
    }
  }

  async function handleLoadPrevious(): Promise<void> {
    if (isLoadingMore || !oldestWeekStart) return

    const token = getSessionToken()
    if (!token) { clearSession(); onclearauth(); return }

    isLoadingMore = true
    const prevWeekEnd = new Date(oldestWeekStart.getTime())
    const prevWeekStart = new Date(oldestWeekStart.getTime() - 7 * 24 * 60 * 60 * 1000)

    try {
      const logWindow = await listEntries(token, prevWeekStart.toISOString(), prevWeekEnd.toISOString())
      oldestWeekStart = prevWeekStart
      const newMessages = logWindow.entries.map(entryToMessage)
      messages = [...newMessages, ...messages]
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      if (handleAuthError(msg)) return
    } finally {
      isLoadingMore = false
    }
  }

  function handleInputKeydown(e: KeyboardEvent): void {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      handleSend()
    }
  }
</script>

{#if currentPage === 'profile'}
  <ProfilePage onback={() => { currentPage = 'chat' }} {onclearauth} />
{:else}
  <div class="flex flex-col h-screen bg-gray-50">
    <!-- Header -->
    <header class="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white shrink-0">
      <span class="font-semibold text-gray-800 text-sm tracking-tight">chai-s-romashkoi</span>
      <button
        type="button"
        onclick={() => { currentPage = 'profile' }}
        class="relative flex items-center gap-1.5 rounded border border-gray-200 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
      >
        Profile
        {#if pendingCount > 0}
          <span class="inline-flex items-center justify-center rounded-full bg-red-500 px-1.5 py-0.5 text-xs font-semibold text-white leading-none">
            {pendingCount}
          </span>
        {/if}
      </button>
    </header>

    <!-- Load error -->
    {#if loadError}
      <div class="px-4 py-2 shrink-0">
        <p class="rounded border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-600">{loadError}</p>
      </div>
    {/if}

    <!-- Loading more indicator -->
    {#if isLoadingMore}
      <div class="px-4 py-1 shrink-0 text-center">
        <span class="text-xs text-gray-400">Loading earlier entries…</span>
      </div>
    {/if}

    <!-- Message list -->
    <ChatMessageList
      {messages}
      {isLoadingMore}
      onloadprevious={handleLoadPrevious}
      onedit={handleEdit}
      ondelete={handleDelete}
      onretry={handleRetry}
    />

    <!-- Input bar -->
    <div class="border-t border-gray-200 bg-white px-4 py-3 flex gap-2 items-end shrink-0">
      <textarea
        bind:value={inputText}
        onkeydown={handleInputKeydown}
        rows={2}
        placeholder="Write something… (Ctrl+Enter to send)"
        class="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-800 resize-none focus:border-gray-400 focus:outline-none placeholder:text-gray-400"
      ></textarea>
      <button
        type="button"
        onclick={handleSend}
        disabled={inputText.trim().length === 0 || isSending}
        class="rounded-lg bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50 transition-colors"
      >
        Send
      </button>
    </div>
  </div>
{/if}
