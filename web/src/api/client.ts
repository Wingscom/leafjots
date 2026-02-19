const BASE_URL = '/api'

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${res.status}: ${body}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export function withEntityId(path: string, entityId?: string | null): string {
  if (!entityId) return path
  const sep = path.includes('?') ? '&' : '?'
  return `${path}${sep}entity_id=${entityId}`
}
