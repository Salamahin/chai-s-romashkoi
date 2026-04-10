<script lang="ts">
  import type { RelationRecord } from './relations_service'

  interface Props {
    record: RelationRecord
    onconfirm: (() => void) | null
    onreject: (() => void) | null
    ondelete: (() => void) | null
  }

  const { record, onconfirm, onreject, ondelete }: Props = $props()
</script>

<div class="flex items-center justify-between gap-3 py-2">
  <div class="min-w-0 flex-1">
    <span class="block truncate text-sm text-gray-800">{record.peer_email}</span>
    <span class="block text-xs text-gray-400">{record.label}</span>
  </div>
  <div class="flex shrink-0 items-center gap-2">
    {#if onconfirm !== null}
      <button
        type="button"
        onclick={onconfirm}
        class="rounded bg-gray-800 px-3 py-1 text-xs font-medium text-white hover:bg-gray-700 transition-colors"
      >
        Confirm
      </button>
    {/if}
    {#if onreject !== null}
      <button
        type="button"
        onclick={onreject}
        class="rounded border border-gray-300 px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
      >
        Reject
      </button>
    {/if}
    {#if ondelete !== null}
      <button
        type="button"
        onclick={ondelete}
        class="rounded border border-gray-300 px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
      >
        Delete
      </button>
    {/if}
  </div>
</div>
