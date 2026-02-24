const BASE_URL = import.meta.env.VITE_BASE_URL 
const PORT = import.meta.env.VITE_PORT_API 

const BASE_PATH = '/api'
const API_URL = `${BASE_URL}:${PORT}${BASE_PATH}`

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
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
