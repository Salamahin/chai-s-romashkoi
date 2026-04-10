export async function assertOk(res: Response): Promise<void> {
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`)
  }
}
