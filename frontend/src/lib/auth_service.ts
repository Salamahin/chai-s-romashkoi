import { tracedFetch } from './http_utils'

const SESSION_KEY = 'session'

interface StoredSession {
  raw: string
  expiresAtMs: number
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
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
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
  const raw = sessionStorage.getItem(SESSION_KEY)
  if (!raw) return null
  try {
    const session = JSON.parse(raw) as StoredSession
    if (session.expiresAtMs <= Date.now()) {
      sessionStorage.removeItem(SESSION_KEY)
      return null
    }
    return session.raw
  } catch {
    sessionStorage.removeItem(SESSION_KEY)
    return null
  }
}

export function clearSession(): void {
  sessionStorage.removeItem(SESSION_KEY)
}
