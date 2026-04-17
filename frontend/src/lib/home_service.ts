export interface HomeData {
  message: string
  pending_relations_count: number
}

import { assertOk, tracedFetch } from './http_utils'

const apiUrl = (import.meta.env.VITE_API_URL as string | undefined) ?? ''
console.log('[home] VITE_API_URL =', apiUrl || '(empty → relative paths)')

export async function getHomeData(sessionToken: string): Promise<HomeData> {
  const url = apiUrl !== '' ? apiUrl : '/'
  const res = await tracedFetch(url, {
    headers: { Authorization: `Bearer ${sessionToken}` },
  })
  await assertOk(res)
  return (await res.json()) as HomeData
}
