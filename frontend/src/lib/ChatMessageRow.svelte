<script lang="ts">
  import type { ChatMessage } from './chat_types'

  interface Props {
    message: ChatMessage
    onedit: (newText: string) => void
    ondelete: () => void
    onretry?: () => void
  }

  const { message, onedit, ondelete, onretry }: Props = $props()

  let localEditing = $state(false)
  let editText = $state('')

  function startEdit(): void {
    editText = message.raw_text
    localEditing = true
  }

  function cancelEdit(): void {
    localEditing = false
  }

  function saveEdit(): void {
    if (editText.trim().length === 0) return
    onedit(editText.trim())
    localEditing = false
  }

  function handleKeydown(e: KeyboardEvent): void {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      saveEdit()
    } else if (e.key === 'Escape') {
      cancelEdit()
    }
  }

  const formattedTime = $derived(new Date(message.logged_at).toLocaleString())
</script>

<div class="group flex flex-col items-end gap-1">
  {#if localEditing}
    <div class="w-full max-w-xs sm:max-w-sm md:max-w-md flex flex-col gap-2">
      <textarea
        bind:value={editText}
        onkeydown={handleKeydown}
        rows={3}
        class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 resize-none focus:border-gray-500 focus:outline-none"
      ></textarea>
      <div class="flex gap-2 justify-end">
        <button
          type="button"
          onclick={cancelEdit}
          class="rounded border border-gray-300 px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
        >
          Cancel
        </button>
        <button
          type="button"
          onclick={saveEdit}
          disabled={editText.trim().length === 0}
          class="rounded bg-gray-800 px-3 py-1 text-xs font-medium text-white hover:bg-gray-700 disabled:opacity-50 transition-colors"
        >
          Save
        </button>
      </div>
    </div>
  {:else}
    <div class="relative max-w-xs sm:max-w-sm md:max-w-md">
      <!-- Action buttons (hover-reveal) -->
      {#if message.delivery === 'saved'}
        <div class="absolute -left-16 top-1 hidden group-hover:flex items-center gap-1">
          <button
            type="button"
            onclick={startEdit}
            class="rounded p-1 text-xs text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
            aria-label="Edit"
          >
            ✎
          </button>
          <button
            type="button"
            onclick={ondelete}
            class="rounded p-1 text-xs text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"
            aria-label="Delete"
          >
            ✕
          </button>
        </div>
      {/if}

      <!-- Bubble -->
      <div
        class="rounded-2xl rounded-tr-sm px-4 py-2 text-sm leading-relaxed whitespace-pre-wrap break-words"
        class:bg-gray-800={message.delivery !== 'failed'}
        class:text-white={message.delivery !== 'failed'}
        class:bg-red-50={message.delivery === 'failed'}
        class:text-red-800={message.delivery === 'failed'}
        class:border={message.delivery === 'failed'}
        class:border-red-200={message.delivery === 'failed'}
      >
        {message.raw_text}
      </div>
    </div>

    <!-- Meta row -->
    <div class="flex items-center gap-2 text-xs text-gray-400 px-1">
      <span>{formattedTime}</span>

      {#if message.isEdited}
        <span class="text-gray-400">edited</span>
      {/if}

      {#if message.delivery === 'pending'}
        <span title="Sending">⏳</span>
      {:else if message.delivery === 'saved'}
        <span class="text-green-500" title="Saved">✓</span>
      {:else if message.delivery === 'failed'}
        <span class="text-red-500" title="Failed">✕</span>
        {#if onretry}
          <button
            type="button"
            onclick={onretry}
            class="rounded border border-red-300 px-2 py-0.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors"
          >
            Retry
          </button>
        {/if}
      {/if}
    </div>
  {/if}
</div>
