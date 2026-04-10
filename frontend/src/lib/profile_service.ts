export interface ProfileEntry {
  entry_id: string
  tag: string
  text: string
  updated_at: string
}

export interface ProfileSnapshot {
  entries: ProfileEntry[]
}

const apiUrl = import.meta.env.VITE_API_URL as string

async function assertOk(res: Response): Promise<void> {
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`)
  }
}

export async function getProfile(sessionToken: string): Promise<ProfileSnapshot> {
  const res = await fetch(`${apiUrl}/profile`, {
    headers: { Authorization: `Bearer ${sessionToken}` },
  })
  await assertOk(res)
  return (await res.json()) as ProfileSnapshot
}

export async function saveProfile(
  sessionToken: string,
  snapshot: ProfileSnapshot,
): Promise<ProfileSnapshot> {
  const res = await fetch(`${apiUrl}/profile`, {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${sessionToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(snapshot),
  })
  await assertOk(res)
  return (await res.json()) as ProfileSnapshot
}

export async function getKnownTags(sessionToken: string): Promise<string[]> {
  const res = await fetch(`${apiUrl}/profile/tags`, {
    headers: { Authorization: `Bearer ${sessionToken}` },
  })
  await assertOk(res)
  const data = (await res.json()) as { tags: string[] }
  return data.tags
}
