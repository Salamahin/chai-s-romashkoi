<script lang="ts">
  interface Props {
    value: string
    options: string[]
    onchange: (normalised: string) => void
    placeholder?: string
  }

  const { value, options, onchange, placeholder = 'Label' }: Props = $props()

  let showSuggestions = $state(false)

  const filtered = $derived(
    options.filter(
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
    class="w-full rounded border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 placeholder-gray-400 outline-none focus:border-gray-400 transition-colors"
  />
  {#if showSuggestions && filtered.length > 0}
    <ul class="absolute z-10 mt-1 w-full rounded border border-gray-200 bg-white shadow-sm text-sm">
      {#each filtered as suggestion}
        <li>
          <button
            type="button"
            class="w-full px-3 py-1.5 text-left text-gray-700 hover:bg-gray-50 transition-colors"
            onmousedown={() => selectSuggestion(suggestion)}
          >
            {suggestion}
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</div>
