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

export interface KPISummary {
  total_entries: number
  total_inflow_usd: number
  total_outflow_usd: number
  net_flow_usd: number
  total_gas_usd: number
  unique_symbols: number
  unique_protocols: number
  active_wallets: number
  avg_tx_value_usd: number
}

export interface CashFlowPeriod {
  period: string
  inflow_usd: number
  outflow_usd: number
  net_usd: number
}

export interface SymbolVolume {
  symbol: string
  volume_usd: number
  trade_count: number
  avg_trade_usd: number
}

export interface ProtocolVolume {
  protocol: string
  volume_usd: number
  entry_count: number
  unique_symbols: number
}

export interface CompositionItem {
  account_type: string
  account_subtype: string | null
  symbol: string
  balance_usd: number
  balance_quantity: number
}

export interface ActivityDay {
  date: string
  entry_count: number
  volume_usd: number
}

export interface EntryTypeBreakdown {
  entry_type: string
  count: number
  volume_usd: number
  gas_usd: number
}

export interface IncomeExpensePeriod {
  period: string
  income_usd: number
  expense_usd: number
  net_usd: number
}

export interface BalancePeriod {
  period: string
  symbol: string
  balance_quantity: number
  balance_usd: number
}

export interface WalletFlow {
  wallet_id: string
  wallet_label: string
  chain: string
  inflow_usd: number
  outflow_usd: number
  net_usd: number
}

export interface ChainFlow {
  chain: string
  inflow_usd: number
  outflow_usd: number
  net_usd: number
  entry_count: number
}

export interface OverviewResponse {
  kpi: KPISummary
  top_symbols: SymbolVolume[]
  top_protocols: ProtocolVolume[]
  recent_activity: ActivityDay[]
}

// ---- Tax analytics response interfaces ----

export interface RealizedGainsPeriod {
  period: string
  total_gain_usd: number
  total_loss_usd: number
  net_gain_usd: number
  trade_count: number
}

export interface GainsBySymbol {
  symbol: string
  total_gain_usd: number
  total_loss_usd: number
  net_gain_usd: number
  lot_count: number
  avg_holding_days: number
}

export interface HoldingBucket {
  bucket_label: string
  min_days: number
  max_days: number | null
  count: number
  total_gain_usd: number
}

export interface WinnersLosers {
  winners: GainsBySymbol[]
  losers: GainsBySymbol[]
}

export interface TaxBreakdownPeriod {
  period: string
  total_tax_vnd: number
  exempt_vnd: number
  taxable_vnd: number
  transfer_count: number
}

export interface TaxByCategory {
  category: string
  total_tax_vnd: number
  transfer_count: number
  volume_usd: number
}

export interface UnrealizedPosition {
  symbol: string
  total_quantity: number
  cost_basis_usd: number
  current_value_usd: number | null
  unrealized_gain_usd: number | null
  lot_count: number
}

export interface CostBasisItem {
  symbol: string
  buy_date: string
  quantity: number
  cost_basis_per_unit_usd: number
  total_cost_usd: number
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

export function fetchGainsOverTime(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<RealizedGainsPeriod[]> {
  return apiFetch<RealizedGainsPeriod[]>(analyticsPath('gains-over-time', filters, entityId))
}

export function fetchGainsBySymbol(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<GainsBySymbol[]> {
  return apiFetch<GainsBySymbol[]>(analyticsPath('gains-by-symbol', filters, entityId))
}

export function fetchHoldingDistribution(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<HoldingBucket[]> {
  return apiFetch<HoldingBucket[]>(analyticsPath('holding-distribution', filters, entityId))
}

export function fetchWinnersLosers(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<WinnersLosers> {
  return apiFetch<WinnersLosers>(analyticsPath('winners-losers', filters, entityId))
}

export function fetchTaxBreakdown(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<TaxBreakdownPeriod[]> {
  return apiFetch<TaxBreakdownPeriod[]>(analyticsPath('breakdown', filters, entityId))
}

export function fetchTaxByCategory(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<TaxByCategory[]> {
  return apiFetch<TaxByCategory[]>(analyticsPath('by-category', filters, entityId))
}

export function fetchUnrealized(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<UnrealizedPosition[]> {
  return apiFetch<UnrealizedPosition[]>(analyticsPath('unrealized', filters, entityId))
}

export function fetchCostBasis(filters: AnalyticsFilters = {}, entityId?: string | null): Promise<CostBasisItem[]> {
  return apiFetch<CostBasisItem[]>(analyticsPath('cost-basis', filters, entityId))
}
