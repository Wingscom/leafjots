import { apiFetch, withEntityId } from './client'

export interface Transaction {
  id: number
  wallet_id: string
  chain: string
  tx_hash: string
  block_number: number | null
  timestamp: number | null
  from_addr: string | null
  to_addr: string | null
  value_wei: number | null
  gas_used: number | null
  status: string
  entry_type: string | null
  created_at: string
}

export interface TransactionDetail extends Transaction {
  tx_data: string | null
  updated_at: string
}

export interface TransactionList {
  transactions: Transaction[]
  total: number
  limit: number
  offset: number
}

export interface TransactionFilters {
  wallet_id?: string
  chain?: string
  status?: string
  limit?: number
  offset?: number
  date_from?: string
  date_to?: string
}

export async function listTransactions(filters: TransactionFilters = {}, entityId?: string): Promise<TransactionList> {
  const params = new URLSearchParams()
  if (filters.wallet_id) params.set('wallet_id', filters.wallet_id)
  if (filters.chain) params.set('chain', filters.chain)
  if (filters.status) params.set('status', filters.status)
  if (filters.limit) params.set('limit', String(filters.limit))
  if (filters.offset !== undefined) params.set('offset', String(filters.offset))
  if (filters.date_from) params.set('date_from', filters.date_from)
  if (filters.date_to) params.set('date_to', filters.date_to)

  const qs = params.toString()
  const path = `/transactions${qs ? `?${qs}` : ''}`
  return apiFetch<TransactionList>(withEntityId(path, entityId))
}

export async function getTransaction(txHash: string): Promise<TransactionDetail> {
  return apiFetch<TransactionDetail>(`/transactions/${txHash}`)
}
