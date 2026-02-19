import { apiFetch, withEntityId } from './client'

export interface JournalSplit {
  id: string
  account_id: string
  account_label: string
  account_type: string
  symbol: string
  quantity: number
  value_usd: number | null
  value_vnd: number | null
}

export interface JournalEntry {
  id: string
  entity_id: string
  transaction_id: string
  entry_type: string
  description: string
  timestamp: string
  created_at: string
}

export interface JournalEntryDetail extends JournalEntry {
  splits: JournalSplit[]
}

export interface JournalList {
  entries: JournalEntry[]
  total: number
  limit: number
  offset: number
}

export interface JournalFilters {
  entry_type?: string
  limit?: number
  offset?: number
}

export async function listJournalEntries(filters: JournalFilters = {}, entityId?: string): Promise<JournalList> {
  const params = new URLSearchParams()
  if (filters.entry_type) params.set('entry_type', filters.entry_type)
  if (filters.limit) params.set('limit', String(filters.limit))
  if (filters.offset !== undefined) params.set('offset', String(filters.offset))
  const qs = params.toString()
  const path = `/journal${qs ? `?${qs}` : ''}`
  return apiFetch<JournalList>(withEntityId(path, entityId))
}

export async function getJournalEntry(id: string): Promise<JournalEntryDetail> {
  return apiFetch<JournalEntryDetail>(`/journal/${id}`)
}

export async function listUnbalanced(entityId?: string): Promise<JournalList> {
  return apiFetch<JournalList>(withEntityId('/journal/validation', entityId))
}
