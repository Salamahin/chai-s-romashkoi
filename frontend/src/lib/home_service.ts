export interface HomeData {
  message: string
  pending_relations_count: number
}

import { assertOk } from './http_utils'

const apiUrl = (import.meta.env.VITE_API_URL as string | undefined) ?? ''

export async function getHomeData(sessionToken: string): Promise<HomeData> {
  if (!apiUrl) return { message: '', pending_relations_count: 0 }
  const res = await fetch(apiUrl, {
    headers: { Authorization: `Bearer ${sessionToken}` },
  })
  await assertOk(res)
  return (await res.json()) as HomeData
}
