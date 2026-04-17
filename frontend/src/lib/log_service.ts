import { assertOk, tracedFetch } from './http_utils'

const apiUrl: string =
  ((import.meta.env.VITE_LOG_API_URL as string | undefined) ?? '').replace(/\/$/, '')
console.log('[log] VITE_LOG_API_URL =', apiUrl || '(empty → relative paths)')

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
  const qs = `?week_start=${encodeURIComponent(weekStart)}&week_end=${encodeURIComponent(weekEnd)}`
  const res = await tracedFetch(`${apiUrl}/log${qs}`, {
    headers: { Authorization: `Bearer ${sessionToken}` },
  })
  await assertOk(res)
  return (await res.json()) as LogWindow
}

export async function createEntry(sessionToken: string, text: string): Promise<LogEntry> {
  const res = await tracedFetch(`${apiUrl}/log`, {
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
  const res = await tracedFetch(`${apiUrl}/log/${entryId}`, {
    method: 'PUT',
    headers: { Authorization: `Bearer ${sessionToken}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
  await assertOk(res)
  return (await res.json()) as LogEntry
}

export async function deleteEntry(sessionToken: string, entryId: string): Promise<void> {
  const res = await tracedFetch(`${apiUrl}/log/${entryId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${sessionToken}` },
  })
  await assertOk(res)
}
