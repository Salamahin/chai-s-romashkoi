import { tracedFetch } from './http_utils'

const SESSION_KEY = 'session'

interface StoredSession {
  raw: string
  expiresAtMs: number
}

declare const google: {
  accounts: {
    id: {
      initialize(config: {
        client_id: string
        callback: (r: { credential: string }) => void
        auto_select?: boolean
      }): void
      prompt(momentListener: (notification: {
        isNotDisplayed(): boolean
        isSkippedMoment(): boolean
      }) => void): void
    }
  }
}

function decodeExp(token: string): number {
  const parts = token.split('.')
  if (parts.length !== 3) return 0
  const payload = JSON.parse(atob(parts[1])) as { exp?: number }
  return (payload.exp ?? 0) * 1000
}

export function storeSessionToken(raw: string): void {
  const session: StoredSession = {
    raw,
    expiresAtMs: decodeExp(raw),
  }
  localStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

const _authApiUrl = (import.meta.env.VITE_API_URL as string | undefined) ?? ''
console.log('[auth] VITE_API_URL =', _authApiUrl || '(empty → relative paths)')

export async function exchangeToken(googleIdToken: string): Promise<void> {
  const res = await tracedFetch(`${_authApiUrl}/auth/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ credential: googleIdToken }),
  })
  if (!res.ok) {
    throw new Error('Sign-in failed. Please try again.')
  }
  const data = (await res.json()) as { session_token: string }
  storeSessionToken(data.session_token)
}

export function getSessionToken(): string | null {
  const raw = localStorage.getItem(SESSION_KEY)
  if (!raw) return null
  try {
    const session = JSON.parse(raw) as StoredSession
    if (session.expiresAtMs <= Date.now()) {
      localStorage.removeItem(SESSION_KEY)
      return null
    }
    return session.raw
  } catch {
    localStorage.removeItem(SESSION_KEY)
    return null
  }
}

export function isSessionStale(): boolean {
  const raw = localStorage.getItem(SESSION_KEY)
  if (!raw) return false
  try {
    const session = JSON.parse(raw) as StoredSession
    return session.expiresAtMs <= Date.now()
  } catch {
    return false
  }
}

export function clearSession(): void {
  localStorage.removeItem(SESSION_KEY)
}

function loadGsiScript(): Promise<void> {
  return new Promise((resolve) => {
    if (document.querySelector('script[src*="gsi/client"]')) {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.defer = true
    script.onload = () => resolve()
    document.head.appendChild(script)
  })
}

export function silentRefresh(onSuccess: () => void, onFailure: () => void): void {
  loadGsiScript().then(() => {
    google.accounts.id.initialize({
      client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID as string,
      callback: ({ credential }) => {
        exchangeToken(credential).then(onSuccess).catch(onFailure)
      },
    })
    google.accounts.id.prompt((notification) => {
      if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
        onFailure()
      }
    })
  }).catch(onFailure)
}
