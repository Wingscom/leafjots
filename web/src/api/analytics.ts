import { apiFetch, withEntityId } from './client'

// ---- Shared filter interface ----

export interface AnalyticsFilters {
  date_from?: string
  date_to?: string
  wallet_id?: string
  chain?: string
  symbol?: string
  entry_type?: string
  account_type?: string
  protocol?: string
  account_subtype?: string
  granularity?: string
}

// ---- General analytics response interfaces ----
// Aligned with backend Pydantic schemas in schemas/analytics.py

export interface KPISummary {
  total_inflow_usd: number
  total_inflow_vnd: number
  total_outflow_usd: number
  total_outflow_vnd: number
  net_usd: number
  net_vnd: number
  total_entries: number
  total_txs: number
  unique_tokens: number
  unique_protocols: number
}

export interface CashFlowPeriod {
  period: string
  inflow_usd: number
  inflow_vnd: number
  outflow_usd: number
  outflow_vnd: number
  net_usd: number
  net_vnd: number
  inflow_qty: number
  outflow_qty: number
  entry_count: number
}

export interface SymbolVolume {
  symbol: string | null
  volume_usd: number
  inflow_usd: number
  outflow_usd: number
  tx_count: number
  total_quantity: number
}

export interface ProtocolVolume {
  protocol: string | null
  volume_usd: number
  tx_count: number
  entry_types: string[]
}

export interface CompositionItem {
  account_type: string
  subtype: string | null
  symbol: string | null
  protocol: string | null
  balance_qty: number
  balance_usd: number
  balance_vnd: number
}

export interface ActivityDay {
  date: string | null
  count: number
  volume_usd: number
}

export interface EntryTypeBreakdown {
  entry_type: string | null
  count: number
  volume_usd: number
}

export interface IncomeExpensePeriod {
  period: string
  income_usd: number
  income_vnd: number
  expense_usd: number
  expense_vnd: number
  income_count: number
  expense_count: number
}

export interface BalancePeriod {
  period: string
  symbol: string
  period_change: number
  cumulative_qty: number
  period_value_usd: number
}

export interface WalletFlow {
  wallet_id: string
  label: string | null
  chain: string | null
  inflow_usd: number
  outflow_usd: number
  net_usd: number
  tx_count: number
}

export interface ChainFlow {
  chain: string | null
  inflow_usd: number
  outflow_usd: number
  net_usd: number
  tx_count: number
}

export interface OverviewResponse {
  kpi: KPISummary
  cash_flow: CashFlowPeriod[]
  composition: CompositionItem[]
}

// ---- Tax analytics response interfaces ----

export interface RealizedGainsPeriod {
  period: string | null
  gains_usd: number
  losses_usd: number
  net_usd: number
  lot_count: number
}

export interface GainsBySymbol {
  symbol: string | null
  gains_usd: number
  losses_usd: number
  net_usd: number
  lot_count: number
  avg_holding_days: number
}

export interface HoldingBucket {
  bucket: string
  lot_count: number
  total_gain_usd: number
  total_quantity: number
}

export interface WinnersLosersItem {
  symbol: string | null
  net_gain_usd: number
  lot_count: number
}

export interface WinnersLosers {
  winners: WinnersLosersItem[]
  losers: WinnersLosersItem[]
}

export interface TaxBreakdownPeriod {
  period: string | null
  taxable_count: number
  exempt_count: number
  total_value_vnd: number
  total_tax_vnd: number
}

export interface TaxByCategory {
  category: string
  transfer_count: number
  total_value_vnd: number
  total_tax_vnd: number
}

export interface UnrealizedPosition {
  symbol: string | null
  remaining_quantity: number
  cost_basis_per_unit_usd: number
  cost_basis_usd: number
  buy_timestamp: string | null
}

export interface CostBasisItem {
  symbol: string | null
  total_quantity: number
  total_cost_usd: number
  avg_cost_per_unit_usd: number
  lot_count: number
}

// ---- Query string builder ----

function buildQueryString(filters: AnalyticsFilters): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value))
    }
  }
  return params.toString()
}

function analyticsPath(endpoint: string, filters: AnalyticsFilters, entityId?: string | null): string {
  const qs = buildQueryString(filters)
  const path = `/analytics/${endpoint}${qs ? `?${qs}` : ''}`
  return withEntityId(path, entityId)
}

// ---- General analytics fetch functions ----

export function fetchOverview(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<OverviewResponse> {
  return apiFetch<OverviewResponse>(analyticsPath('overview', filters, entityId))
}

export function fetchCashFlow(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<CashFlowPeriod[]> {
  return apiFetch<CashFlowPeriod[]>(analyticsPath('cash-flow', filters, entityId))
}

export function fetchIncomeExpense(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<IncomeExpensePeriod[]> {
  return apiFetch<IncomeExpensePeriod[]>(analyticsPath('income-expense', filters, entityId))
}

export function fetchBalanceOverTime(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<BalancePeriod[]> {
  return apiFetch<BalancePeriod[]>(analyticsPath('balance-over-time', filters, entityId))
}

export function fetchTopSymbols(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<SymbolVolume[]> {
  return apiFetch<SymbolVolume[]>(analyticsPath('top-symbols', filters, entityId))
}

export function fetchTopProtocols(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<ProtocolVolume[]> {
  return apiFetch<ProtocolVolume[]>(analyticsPath('top-protocols', filters, entityId))
}

export function fetchComposition(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<CompositionItem[]> {
  return apiFetch<CompositionItem[]>(analyticsPath('composition', filters, entityId))
}

export function fetchActivity(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<ActivityDay[]> {
  return apiFetch<ActivityDay[]>(analyticsPath('activity', filters, entityId))
}

export function fetchEntryTypes(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<EntryTypeBreakdown[]> {
  return apiFetch<EntryTypeBreakdown[]>(analyticsPath('entry-types', filters, entityId))
}

export function fetchFlowByWallet(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<WalletFlow[]> {
  return apiFetch<WalletFlow[]>(analyticsPath('flow-by-wallet', filters, entityId))
}

export function fetchFlowByChain(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<ChainFlow[]> {
  return apiFetch<ChainFlow[]>(analyticsPath('flow-by-chain', filters, entityId))
}

// ---- Tax analytics fetch functions ----
// Note: backend tax endpoints are under /analytics/tax/...

export function fetchGainsOverTime(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<RealizedGainsPeriod[]> {
  return apiFetch<RealizedGainsPeriod[]>(analyticsPath('tax/gains-over-time', filters, entityId))
}

export function fetchGainsBySymbol(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<GainsBySymbol[]> {
  return apiFetch<GainsBySymbol[]>(analyticsPath('tax/gains-by-symbol', filters, entityId))
}

export function fetchHoldingDistribution(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<HoldingBucket[]> {
  return apiFetch<HoldingBucket[]>(analyticsPath('tax/holding-distribution', filters, entityId))
}

export function fetchWinnersLosers(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<WinnersLosers> {
  return apiFetch<WinnersLosers>(analyticsPath('tax/winners-losers', filters, entityId))
}

export function fetchTaxBreakdown(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<TaxBreakdownPeriod[]> {
  return apiFetch<TaxBreakdownPeriod[]>(analyticsPath('tax/breakdown', filters, entityId))
}

export function fetchTaxByCategory(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<TaxByCategory[]> {
  return apiFetch<TaxByCategory[]>(analyticsPath('tax/by-category', filters, entityId))
}

export function fetchUnrealized(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<UnrealizedPosition[]> {
  return apiFetch<UnrealizedPosition[]>(analyticsPath('tax/unrealized', filters, entityId))
}

export function fetchCostBasis(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<CostBasisItem[]> {
  return apiFetch<CostBasisItem[]>(analyticsPath('tax/cost-basis', filters, entityId))
}
