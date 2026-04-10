<script lang="ts">
  import TagCombobox from './TagCombobox.svelte'

  export interface ProfileEntry {
    id: string
    tag: string
    text: string
    updated_at: string
  }

  interface Props {
    entry: ProfileEntry
    tagSuggestions: string[]
    onchange: (updated: ProfileEntry) => void
    ondelete: () => void
  }

  const { entry, tagSuggestions, onchange, ondelete }: Props = $props()

  function handleTagChange(tag: string): void {
    onchange({ ...entry, tag, updated_at: new Date().toISOString() })
  }

  function handleTextInput(e: Event): void {
    const text = (e.currentTarget as HTMLTextAreaElement).value
    onchange({ ...entry, text, updated_at: new Date().toISOString() })
  }
</script>

<div class="py-4">
  <div class="flex items-center gap-1 mb-2">
    <span class="text-base font-semibold text-gray-400 select-none">#</span>
    <div class="flex-1">
      <TagCombobox
        value={entry.tag}
        suggestions={tagSuggestions}
        onchange={handleTagChange}
        placeholder="tag"
      />
    </div>
    <button
      type="button"
      onclick={ondelete}
      aria-label="Delete entry"
      class="shrink-0 rounded p-1 text-gray-300 hover:text-red-400 transition-colors"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
      </svg>
    </button>
  </div>

  <textarea
    value={entry.text}
    oninput={handleTextInput}
    rows={2}
    placeholder="Write something…"
    class="w-full resize-none rounded border border-gray-200 px-2 py-1.5 text-sm text-gray-700 placeholder-gray-400 outline-none focus:border-gray-400 focus:ring-1 focus:ring-gray-300 transition-colors"
  ></textarea>
</div>
