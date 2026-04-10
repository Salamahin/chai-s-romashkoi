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

export async function exchangeToken(_googleIdToken: string): Promise<void> {
  const apiUrl = import.meta.env.VITE_API_URL as string
  const res = await fetch(`${apiUrl}/auth/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  if (!res.ok) {
    throw new Error(`Token exchange failed: ${res.status}`)
  }
  const data = (await res.json()) as { session_token: string }
  const session: StoredSession = {
    raw: data.session_token,
    expiresAtMs: decodeExp(data.session_token),
  }
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
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
