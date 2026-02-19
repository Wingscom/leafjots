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

export function getRealizedGains(entityId?: string) {
  return apiFetch<ClosedLotResponse[]>(withEntityId('/tax/realized-gains', entityId))
}

export function getOpenLots(entityId?: string) {
  return apiFetch<OpenLotResponse[]>(withEntityId('/tax/open-lots', entityId))
}

export function getTaxSummary(entityId?: string) {
  return apiFetch<TaxSummaryResponse | null>(withEntityId('/tax/summary', entityId))
}
