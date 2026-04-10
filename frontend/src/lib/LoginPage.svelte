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

<div class="flex items-center justify-center h-screen bg-white">
  <div bind:this={buttonDiv}></div>
</div>
