import { assertOk } from './http_utils'

const apiUrl: string =
  (import.meta.env.VITE_LOG_API_URL as string | undefined) ?? 'http://localhost:8000'

export interface LogEntry {
  entry_id: string
  raw_text: string
  logged_at: string
  updated_at: string
}

export interface LogWindow {
  entries: LogEntry[]
}

export async function listEntries(
  sessionToken: string,
  weekStart: string,
  weekEnd: string,
): Promise<LogWindow> {
  const url = new URL(`${apiUrl}/log`)
  url.searchParams.set('week_start', weekStart)
  url.searchParams.set('week_end', weekEnd)
  const res = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${sessionToken}` },
  })
  await assertOk(res)
  return (await res.json()) as LogWindow
}

export async function createEntry(sessionToken: string, text: string): Promise<LogEntry> {
  const res = await fetch(`${apiUrl}/log`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${sessionToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  await assertOk(res)
  return (await res.json()) as LogEntry
}

export async function editEntry(
  sessionToken: string,
  entryId: string,
  text: string,
): Promise<LogEntry> {
  const res = await fetch(`${apiUrl}/log/${entryId}`, {
    method: 'PUT',
    headers: { Authorization: `Bearer ${sessionToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  await assertOk(res)
  return (await res.json()) as LogEntry
}

export async function deleteEntry(sessionToken: string, entryId: string): Promise<void> {
  const res = await fetch(`${apiUrl}/log/${entryId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${sessionToken}` },
  })
  await assertOk(res)
}
