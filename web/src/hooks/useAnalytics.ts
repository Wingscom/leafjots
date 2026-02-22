import { useQuery } from '@tanstack/react-query'
import { useEntity } from '../context/EntityContext'
import {
  fetchOverview,
  fetchCashFlow,
  fetchIncomeExpense,
  fetchBalanceOverTime,
  fetchTopSymbols,
  fetchTopProtocols,
  fetchComposition,
  fetchActivity,
  fetchEntryTypes,
  fetchFlowByWallet,
  fetchFlowByChain,
  fetchGainsOverTime,
  fetchGainsBySymbol,
  fetchHoldingDistribution,
  fetchWinnersLosers,
  fetchTaxBreakdown,
  fetchTaxByCategory,
  fetchUnrealized,
  fetchCostBasis,
  type AnalyticsFilters,
} from '../api/analytics'

const ANALYTICS_KEY = ['analytics'] as const

// ---- General analytics hooks ----

export function useOverview(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'overview', entityId, filters],
    queryFn: () => fetchOverview(filters, entityId),
  })
}

export function useCashFlow(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'cash-flow', entityId, filters],
    queryFn: () => fetchCashFlow(filters, entityId),
  })
}

export function useIncomeExpense(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'income-expense', entityId, filters],
    queryFn: () => fetchIncomeExpense(filters, entityId),
  })
}

export function useBalanceOverTime(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'balance-over-time', entityId, filters],
    queryFn: () => fetchBalanceOverTime(filters, entityId),
  })
}

export function useTopSymbols(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'top-symbols', entityId, filters],
    queryFn: () => fetchTopSymbols(filters, entityId),
  })
}

export function useTopProtocols(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'top-protocols', entityId, filters],
    queryFn: () => fetchTopProtocols(filters, entityId),
  })
}

export function useComposition(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'composition', entityId, filters],
    queryFn: () => fetchComposition(filters, entityId),
  })
}

export function useActivity(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'activity', entityId, filters],
    queryFn: () => fetchActivity(filters, entityId),
  })
}

export function useEntryTypes(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'entry-types', entityId, filters],
    queryFn: () => fetchEntryTypes(filters, entityId),
  })
}

export function useFlowByWallet(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'flow-by-wallet', entityId, filters],
    queryFn: () => fetchFlowByWallet(filters, entityId),
  })
}

export function useFlowByChain(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'flow-by-chain', entityId, filters],
    queryFn: () => fetchFlowByChain(filters, entityId),
  })
}

// ---- Tax analytics hooks ----

export function useGainsOverTime(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'gains-over-time', entityId, filters],
    queryFn: () => fetchGainsOverTime(filters, entityId),
  })
}

export function useGainsBySymbol(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'gains-by-symbol', entityId, filters],
    queryFn: () => fetchGainsBySymbol(filters, entityId),
  })
}

export function useHoldingDistribution(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'holding-distribution', entityId, filters],
    queryFn: () => fetchHoldingDistribution(filters, entityId),
  })
}

export function useWinnersLosers(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'winners-losers', entityId, filters],
    queryFn: () => fetchWinnersLosers(filters, entityId),
  })
}

export function useTaxBreakdown(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'tax-breakdown', entityId, filters],
    queryFn: () => fetchTaxBreakdown(filters, entityId),
  })
}

export function useTaxByCategory(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'tax-by-category', entityId, filters],
    queryFn: () => fetchTaxByCategory(filters, entityId),
  })
}

export function useUnrealized(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'unrealized', entityId, filters],
    queryFn: () => fetchUnrealized(filters, entityId),
  })
}

export function useCostBasis(filters: AnalyticsFilters = {}) {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...ANALYTICS_KEY, 'cost-basis', entityId, filters],
    queryFn: () => fetchCostBasis(filters, entityId),
  })
}
