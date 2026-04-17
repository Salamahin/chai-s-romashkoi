export type RelationStatus = 'pending' | 'confirmed'
export type RelationDirection = 'sent' | 'received'

export interface RelationRecord {
  relation_id: string
  peer_email: string
  label: string
  status: RelationStatus
  direction: RelationDirection
  created_at: string
}

export interface RelationsSnapshot {
  relations: RelationRecord[]
}

import { assertOk, tracedFetch } from './http_utils'

const baseUrl: string =
  ((import.meta.env.VITE_RELATIONS_API_URL as unknown as string | undefined) ?? '').replace(/\/$/, '')
console.log('[relations] VITE_RELATIONS_API_URL =', baseUrl || '(empty → relative paths)')

export async function listRelations(sessionToken: string): Promise<RelationsSnapshot> {
  const res = await tracedFetch(`${baseUrl}/relations`, {
    headers: { Authorization: `Bearer ${sessionToken}` },
  })
  await assertOk(res)
  return (await res.json()) as RelationsSnapshot
}

export async function sendRelation(
  sessionToken: string,
  recipientEmail: string,
  label: string,
): Promise<RelationRecord> {
  const res = await tracedFetch(`${baseUrl}/relations`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${sessionToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ recipient_email: recipientEmail, label }),
  })
  await assertOk(res)
  return (await res.json()) as RelationRecord
}

export async function confirmRelation(
  sessionToken: string,
  relationId: string,
): Promise<RelationRecord> {
  const res = await tracedFetch(`${baseUrl}/relations/${relationId}/confirm`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${sessionToken}` },
  })
  await assertOk(res)
  return (await res.json()) as RelationRecord
}

export async function deleteRelation(sessionToken: string, relationId: string): Promise<void> {
  const res = await tracedFetch(`${baseUrl}/relations/${relationId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${sessionToken}` },
  })
  await assertOk(res)
}

export async function getKnownLabels(sessionToken: string): Promise<string[]> {
  const res = await tracedFetch(`${baseUrl}/relations/labels`, {
    headers: { Authorization: `Bearer ${sessionToken}` },
  })
  await assertOk(res)
  const data = (await res.json()) as { labels: string[] }
  return data.labels
}
