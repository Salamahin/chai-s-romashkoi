<script lang="ts">
  import type { ChatMessage } from './chat_types'
  import ChatMessageRow from './ChatMessageRow.svelte'

  interface Props {
    messages: ChatMessage[]
    onloadprevious: () => void
    onedit: (localId: string, newText: string) => void
    ondelete: (localId: string) => void
    onretry: (localId: string) => void
  }

  const { messages, onloadprevious, onedit, ondelete, onretry }: Props = $props()

  let listEl: HTMLDivElement | undefined = $state()
  let prevLength = 0
  let prevLastLocalId = ''

  $effect(() => {
    const last = messages[messages.length - 1]
    const lastLocalId = last?.localId ?? ''
    // Only scroll to bottom when a new message is appended (last item changed).
    // Prepending older messages (load-previous) increases length but keeps the last item unchanged.
    if (messages.length > prevLength && lastLocalId !== prevLastLocalId) {
      listEl?.scrollTo({ top: listEl.scrollHeight, behavior: 'smooth' })
    }
    prevLength = messages.length
    prevLastLocalId = lastLocalId
  })

  function handleScroll(): void {
    if (listEl && listEl.scrollTop === 0) {
      onloadprevious()
    }
  }
</script>

<div
  bind:this={listEl}
  onscroll={handleScroll}
  class="flex-1 overflow-y-auto px-4 py-2 flex flex-col gap-2"
>
  {#each messages as message (message.localId)}
    <ChatMessageRow
      {message}
      onedit={(newText) => onedit(message.localId, newText)}
      ondelete={() => ondelete(message.localId)}
      onretry={() => onretry(message.localId)}
    />
  {/each}
</div>
