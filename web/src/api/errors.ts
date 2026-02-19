import { apiFetch, withEntityId } from './client'

export interface DiagnosticData {
  tx_hash?: string
  contract_address?: string
  function_selector?: string
  chain?: string
  detected_transfers?: Array<{
    type: string
    symbol: string
    from: string
    to: string
  }>
  detected_events?: Array<{
    event: string
    address: string
  }>
  parsers_attempted?: Array<{
    parser: string
    matched: boolean
    produced_splits?: boolean
  }>
}

export interface ParseError {
  id: string
  transaction_id: string
  wallet_id: string
  tx_hash: string | null
  chain: string | null
  error_type: string
  message: string
  stack_trace: string | null
  resolved: boolean
  created_at: string
  diagnostic_data: DiagnosticData | null
}

export interface ErrorList {
  errors: ParseError[]
  total: number
  limit: number
  offset: number
}

export interface ErrorSummary {
  total: number
  by_type: Record<string, number>
  resolved: number
  unresolved: number
}

export interface ErrorFilters {
  error_type?: string
  resolved?: boolean
  limit?: number
  offset?: number
}

export async function listErrors(filters: ErrorFilters = {}, entityId?: string): Promise<ErrorList> {
  const params = new URLSearchParams()
  if (filters.error_type) params.set('error_type', filters.error_type)
  if (filters.resolved !== undefined) params.set('resolved', String(filters.resolved))
  if (filters.limit) params.set('limit', String(filters.limit))
  if (filters.offset !== undefined) params.set('offset', String(filters.offset))
  const qs = params.toString()
  const path = `/errors${qs ? `?${qs}` : ''}`
  return apiFetch<ErrorList>(withEntityId(path, entityId))
}

export async function getErrorSummary(entityId?: string): Promise<ErrorSummary> {
  return apiFetch<ErrorSummary>(withEntityId('/errors/summary', entityId))
}

export async function retryError(errorId: string, entityId?: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(withEntityId(`/errors/${errorId}/retry`, entityId), { method: 'POST' })
}

export async function ignoreError(errorId: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/errors/${errorId}/ignore`, { method: 'POST' })
}

export async function retryErrorGroup(contractAddress?: string, functionSelector?: string, entityId?: string): Promise<{ retried: number; success: number; failed: number }> {
  const params = new URLSearchParams()
  if (contractAddress) params.set('contract_address', contractAddress)
  if (functionSelector) params.set('function_selector', functionSelector)
  const qs = params.toString()
  const path = `/errors/retry-group${qs ? `?${qs}` : ''}`
  return apiFetch(withEntityId(path, entityId), { method: 'POST' })
}
