<script module lang="ts">
  declare const google: {
    accounts: {
      id: {
        initialize(config: { client_id: string; callback: (r: { credential: string }) => void; auto_select?: boolean }): void
        renderButton(el: HTMLElement, opts: { theme: string; size: string }): void
      }
    }
  }
</script>

<script lang="ts">
  import { onMount } from 'svelte'
  import { exchangeToken } from './auth_service'

  interface Props {
    onauthenticated: () => void
  }

  const { onauthenticated }: Props = $props()

  let buttonDiv: HTMLDivElement | undefined = $state()
  let scriptReady = $state(false)
  let loginError: string | null = $state(null)

  onMount(() => {
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.defer = true
    script.onload = () => { scriptReady = true }
    document.head.appendChild(script)
  })

  $effect(() => {
    if (!scriptReady || !buttonDiv) return
    google.accounts.id.initialize({
      client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID as string,
      auto_select: true,
      callback: ({ credential }) => {
        loginError = null
        exchangeToken(credential).then(onauthenticated).catch((err) => {
          loginError = err instanceof Error ? err.message : 'Sign-in failed'
        })
      },
    })
    google.accounts.id.renderButton(buttonDiv, { theme: 'outline', size: 'large' })
  })
</script>

<div class="flex min-h-screen items-center justify-center bg-white px-4">
  <div class="w-full max-w-xs text-center">
    <img src="/logo.webp" alt="chai s romashkoi" class="mb-6 mx-auto w-32 h-32 object-contain" />
    <p class="mb-1 font-mono text-sm font-semibold text-gray-800">chai-s-romashkoi</p>
    <p class="mb-6 font-mono text-xs text-gray-400">sign in to continue</p>
    <div class="flex justify-center" bind:this={buttonDiv}></div>
    {#if loginError}
      <p class="mt-4 font-mono text-xs text-red-500">{loginError}</p>
    {/if}
  </div>
</div>
