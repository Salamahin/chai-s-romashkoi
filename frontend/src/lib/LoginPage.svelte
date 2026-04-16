<script module lang="ts">
  declare const google: {
    accounts: {
      id: {
        initialize(config: { client_id: string; callback: (r: { credential: string }) => void }): void
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
      callback: ({ credential }) => {
        exchangeToken(credential).then(onauthenticated).catch(console.error)
      },
    })
    google.accounts.id.renderButton(buttonDiv, { theme: 'outline', size: 'large' })
  })
</script>

<div class="flex min-h-screen items-center justify-center bg-gray-50 px-4">
  <div class="w-full max-w-sm rounded-lg border border-gray-200 bg-white px-8 py-10 text-center">
    <pre class="mb-4 font-mono text-xs leading-tight text-gray-400 text-left inline-block">   * . * . *
  . \ | / .
  *-( o )-*
  . / | \ .
   * . * . *
   _________
  / ~~~~~~~ \
 |           |
  \_________/</pre>
    <h1 class="mb-1 text-lg font-semibold text-gray-800 tracking-tight">Chai s Romashkoi</h1>
    <p class="mb-8 text-sm text-gray-400">Sign in to continue</p>
    <div class="flex justify-center" bind:this={buttonDiv}></div>
  </div>
</div>
