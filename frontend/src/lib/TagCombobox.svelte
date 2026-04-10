<script lang="ts">
  interface Props {
    value: string
    suggestions: string[]
    onchange: (value: string) => void
    placeholder?: string
  }

  const { value, suggestions, onchange, placeholder = 'Tag' }: Props = $props()

  let showSuggestions = $state(false)

  const filtered = $derived(
    suggestions.filter(
      (s) => s.toLowerCase().includes(value.toLowerCase()) && s !== value
    )
  )

  function handleInput(e: Event): void {
    const target = e.currentTarget as HTMLInputElement
    const normalised = target.value.toLowerCase().trim()
    if (normalised !== value) {
      onchange(normalised)
    }
    showSuggestions = true
  }

  function selectSuggestion(s: string): void {
    onchange(s)
    showSuggestions = false
  }

  function handleBlur(): void {
    setTimeout(() => { showSuggestions = false }, 100)
  }
</script>

<div class="relative w-full">
  <input
    type="text"
    value={value}
    oninput={handleInput}
    onblur={handleBlur}
    onfocus={() => { showSuggestions = true }}
    {placeholder}
    class="w-full bg-transparent text-base font-semibold text-gray-800 placeholder-gray-300 outline-none border-none focus:ring-0 transition-colors"
  />
  {#if showSuggestions && filtered.length > 0}
    <ul class="absolute z-10 mt-1 w-full rounded border border-gray-200 bg-white shadow-sm text-sm">
      {#each filtered as suggestion}
        <li>
          <button
            type="button"
            class="w-full px-2 py-1.5 text-left text-gray-700 hover:bg-gray-50 transition-colors"
            onmousedown={() => selectSuggestion(suggestion)}
          >
            {suggestion}
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</div>
