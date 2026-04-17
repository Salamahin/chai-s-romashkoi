export async function assertOk(res: Response): Promise<void> {
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`)
  }
}

export function tracedFetch(input: string | URL | Request, init?: RequestInit): Promise<Response> {
  const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
  console.log('[fetch]', init?.method ?? 'GET', url)
  return fetch(input, init).catch((err: unknown) => {
    console.error('[fetch] network/CORS error →', url, err)
    throw err
  })
}
