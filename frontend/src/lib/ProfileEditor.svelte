<script lang="ts">
  import ProfileEntryRow from './ProfileEntryRow.svelte'
  import type { ProfileEntry } from './ProfileEntryRow.svelte'

  interface Props {
    entries: ProfileEntry[]
    knownTags: string[]
    onchange: (entries: ProfileEntry[]) => void
  }

  const { entries, knownTags, onchange }: Props = $props()

  const allTags = $derived(
    [...new Set([...knownTags, ...entries.map((e) => e.tag)].filter((t) => t.trim() !== ''))]
  )

  function addEntry(): void {
    const newEntry: ProfileEntry = { id: crypto.randomUUID(), tag: '', text: '' }
    onchange([...entries, newEntry])
  }

  function updateEntry(updated: ProfileEntry): void {
    onchange(entries.map((e) => (e.id === updated.id ? updated : e)))
  }

  function deleteEntry(id: string): void {
    onchange(entries.filter((e) => e.id !== id))
  }
</script>

<div>
  <div class="divide-y divide-gray-100">
    {#each entries as entry (entry.id)}
      <ProfileEntryRow
        {entry}
        tagSuggestions={allTags}
        onchange={updateEntry}
        ondelete={() => deleteEntry(entry.id)}
      />
    {/each}
  </div>

  <div class="pt-4">
    <button
      type="button"
      onclick={addEntry}
      class="w-full rounded border border-dashed border-gray-300 py-2 text-sm text-gray-500 hover:border-gray-400 hover:text-gray-700 transition-colors"
    >
      + Add entry
    </button>
  </div>
</div>
