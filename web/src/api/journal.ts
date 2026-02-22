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
  date_from?: string
  date_to?: string
  symbol?: string
  account_type?: string
  wallet_id?: string
  protocol?: string
  account_subtype?: string
}

export async function listJournalEntries(filters: JournalFilters = {}, entityId?: string): Promise<JournalList> {
  const params = new URLSearchParams()
  if (filters.entry_type) params.set('entry_type', filters.entry_type)
  if (filters.limit) params.set('limit', String(filters.limit))
  if (filters.offset !== undefined) params.set('offset', String(filters.offset))
  if (filters.date_from) params.set('date_from', filters.date_from)
  if (filters.date_to) params.set('date_to', filters.date_to)
  if (filters.symbol) params.set('symbol', filters.symbol)
  if (filters.account_type) params.set('account_type', filters.account_type)
  if (filters.wallet_id) params.set('wallet_id', filters.wallet_id)
  if (filters.protocol) params.set('protocol', filters.protocol)
  if (filters.account_subtype) params.set('account_subtype', filters.account_subtype)
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

export interface RepriceResult {
  updated: number
  still_null: number
  total_null_before: number
  unmapped_symbols: string[]
}

export async function repriceJournal(entityId?: string): Promise<RepriceResult> {
  return apiFetch<RepriceResult>(withEntityId('/journal/reprice', entityId), { method: 'POST' })
}
