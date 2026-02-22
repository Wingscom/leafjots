import { apiFetch, withEntityId } from './client'

export interface TaxCalculateRequest {
  entity_id?: string
  start_date: string
  end_date: string
}

export interface TaxSummaryResponse {
  period_start: string
  period_end: string
  total_realized_gain_usd: number
  total_transfer_tax_vnd: number
  total_exempt_vnd: number
  closed_lot_count: number
  open_lot_count: number
  taxable_transfer_count: number
}

export interface ClosedLotResponse {
  symbol: string
  quantity: number
  cost_basis_usd: number
  proceeds_usd: number
  gain_usd: number
  holding_days: number
  buy_date: string
  sell_date: string
}

export interface OpenLotResponse {
  symbol: string
  remaining_quantity: number
  cost_basis_per_unit_usd: number
  buy_date: string
}

export interface TaxableTransferResponse {
  timestamp: string
  symbol: string
  quantity: number
  value_vnd: number
  tax_amount_vnd: number
  exemption_reason: string | null
}

export interface TaxCalculateResponse {
  summary: TaxSummaryResponse
  closed_lots: ClosedLotResponse[]
  open_lots: OpenLotResponse[]
  taxable_transfers: TaxableTransferResponse[]
}

export function calculateTax(body: TaxCalculateRequest) {
  return apiFetch<TaxCalculateResponse>('/tax/calculate', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export interface RealizedGainsFilters {
  symbol?: string
  date_from?: string
  date_to?: string
  gain_only?: boolean
  loss_only?: boolean
}

export interface OpenLotsFilters {
  symbol?: string
  min_quantity?: number
}

export function getRealizedGains(entityId?: string, filters: RealizedGainsFilters = {}) {
  const params = new URLSearchParams()
  if (filters.symbol) params.set('symbol', filters.symbol)
  if (filters.date_from) params.set('date_from', filters.date_from)
  if (filters.date_to) params.set('date_to', filters.date_to)
  if (filters.gain_only !== undefined) params.set('gain_only', String(filters.gain_only))
  if (filters.loss_only !== undefined) params.set('loss_only', String(filters.loss_only))
  const qs = params.toString()
  const path = `/tax/realized-gains${qs ? `?${qs}` : ''}`
  return apiFetch<ClosedLotResponse[]>(withEntityId(path, entityId))
}

export function getOpenLots(entityId?: string, filters: OpenLotsFilters = {}) {
  const params = new URLSearchParams()
  if (filters.symbol) params.set('symbol', filters.symbol)
  if (filters.min_quantity !== undefined) params.set('min_quantity', String(filters.min_quantity))
  const qs = params.toString()
  const path = `/tax/open-lots${qs ? `?${qs}` : ''}`
  return apiFetch<OpenLotResponse[]>(withEntityId(path, entityId))
}

export function getTaxSummary(entityId?: string) {
  return apiFetch<TaxSummaryResponse | null>(withEntityId('/tax/summary', entityId))
}
