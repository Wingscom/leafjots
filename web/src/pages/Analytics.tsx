import { useState, useCallback, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { TrendingUp, TrendingDown, ArrowRightLeft, Coins, RefreshCw, AlertCircle, Hash, Layers, DollarSign } from 'lucide-react'
import {
  useOverview,
  useCashFlow,
  useIncomeExpense,
  useComposition,
  useEntryTypes,
  useTopSymbols,
  useTopProtocols,
  useFlowByWallet,
  useActivity,
} from '../hooks/useAnalytics'
import type { AnalyticsFilters } from '../api/analytics'
import {
  KPICard,
  CashFlowChart,
  IncomeExpenseChart,
  IncomeExpenseCountChart,
  CompositionDonut,
  EntryTypeBar,
  ActivityHeatmap,
} from '../components/charts'
import {
  FilterBar,
  DateRangePicker,
  WalletSelector,
  ChainSelector,
  GranularitySelector,
} from '../components/filters'
import { useWallets } from '../hooks/useWallets'
import DataTable, { type Column } from '../components/DataTable'
import type { SymbolVolume, ProtocolVolume, WalletFlow } from '../api/analytics'
import { repriceJournal } from '../api/journal'
import { useEntity } from '../context/EntityContext'
import { useQueryClient } from '@tanstack/react-query'

function formatUSD(value: number): string {
  if (Math.abs(value) >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(2)}M`
  }
  if (Math.abs(value) >= 1_000) {
    return `$${(value / 1_000).toFixed(1)}k`
  }
  return `$${value.toLocaleString('en-US', { maximumFractionDigits: 2 })}`
}

function SectionError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 flex flex-col items-center justify-center gap-2 h-48">
      <AlertCircle className="w-6 h-6 text-red-400" />
      <p className="text-sm text-gray-500">Failed to load data</p>
      <button
        onClick={onRetry}
        className="text-xs text-blue-600 hover:underline flex items-center gap-1"
      >
        <RefreshCw className="w-3 h-3" /> Retry
      </button>
    </div>
  )
}

function SectionSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 h-48 animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-1/3 mb-4" />
      <div className="h-36 bg-gray-100 rounded" />
    </div>
  )
}

export default function Analytics() {
  const navigate = useNavigate()
  const { entityId } = useEntity()
  const queryClient = useQueryClient()
  const { data: walletsData } = useWallets()
  const [repricing, setRepricing] = useState(false)
  const [repriceResult, setRepriceResult] = useState<string | null>(null)

  const handleReprice = useCallback(async () => {
    setRepricing(true)
    setRepriceResult(null)
    try {
      const result = await repriceJournal(entityId ?? undefined)
      setRepriceResult(`Updated ${result.updated} splits (${result.still_null} still missing${result.unmapped_symbols.length ? `, unmapped: ${result.unmapped_symbols.join(', ')}` : ''})`)
      // Refresh all analytics queries
      queryClient.invalidateQueries({ queryKey: ['analytics'] })
    } catch (err) {
      setRepriceResult(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setRepricing(false)
    }
  }, [entityId, queryClient])

  const walletOptions = (walletsData?.wallets ?? []).map((w) => ({
    id: w.id,
    label: w.label ?? w.address ?? w.id,
  }))

  const [dateFrom, setDateFrom] = useState<string | null>(null)
  const [dateTo, setDateTo] = useState<string | null>(null)
  const [walletId, setWalletId] = useState<string | null>(null)
  const [chain, setChain] = useState<string | null>(null)
  const [granularity, setGranularity] = useState('month')
  const userChangedGranularity = useRef(false)

  const handleGranularityChange = useCallback((value: string) => {
    userChangedGranularity.current = true
    setGranularity(value)
  }, [])

  const handleReset = useCallback(() => {
    setDateFrom(null)
    setDateTo(null)
    setWalletId(null)
    setChain(null)
    setGranularity('month')
    userChangedGranularity.current = false
  }, [])

  const filters: AnalyticsFilters = {
    ...(dateFrom ? { date_from: dateFrom } : {}),
    ...(dateTo ? { date_to: dateTo } : {}),
    ...(walletId ? { wallet_id: walletId } : {}),
    ...(chain ? { chain } : {}),
    granularity,
  }

  const overviewQ = useOverview(filters)
  const cashFlowQ = useCashFlow(filters)
  const incomeExpenseQ = useIncomeExpense(filters)
  const compositionQ = useComposition(filters)
  const entryTypesQ = useEntryTypes(filters)
  const topSymbolsQ = useTopSymbols(filters)
  const topProtocolsQ = useTopProtocols(filters)
  const flowByWalletQ = useFlowByWallet(filters)
  const activityQ = useActivity(filters)

  // Auto-detect best granularity from cash_flow date spread
  useEffect(() => {
    const cashFlow = overviewQ.data?.cash_flow
    if (!cashFlow?.length || userChangedGranularity.current) return
    const timestamps = cashFlow.map((c) => new Date(c.period).getTime()).filter((t) => !isNaN(t))
    if (timestamps.length < 2) {
      // Single period — use day to show individual days
      setGranularity('day')
      return
    }
    const span = Math.max(...timestamps) - Math.min(...timestamps)
    const days = span / (1000 * 60 * 60 * 24)
    if (days < 7) setGranularity('day')
    else if (days < 90) setGranularity('week')
    // else keep 'month'
  }, [overviewQ.data])

  const kpi = overviewQ.data?.kpi

  // Columns for top symbols table
  const symbolColumns: Column<SymbolVolume>[] = [
    { key: 'symbol', header: 'Symbol', sortable: true },
    {
      key: 'total_quantity',
      header: 'Quantity',
      align: 'right',
      sortable: true,
      render: (item) => item.total_quantity.toLocaleString('en-US', { maximumFractionDigits: 4 }),
    },
    {
      key: 'volume_usd',
      header: 'Volume (USD)',
      align: 'right',
      sortable: true,
      render: (item) => formatUSD(item.volume_usd),
    },
    {
      key: 'inflow_usd',
      header: 'Inflow',
      align: 'right',
      render: (item) => <span className="text-green-600">{formatUSD(item.inflow_usd)}</span>,
    },
    {
      key: 'outflow_usd',
      header: 'Outflow',
      align: 'right',
      render: (item) => <span className="text-red-500">{formatUSD(item.outflow_usd)}</span>,
    },
    {
      key: 'tx_count',
      header: 'Entries',
      align: 'right',
      sortable: true,
      render: (item) => item.tx_count.toLocaleString('en-US'),
    },
  ]

  // Columns for top protocols table
  const protocolColumns: Column<ProtocolVolume>[] = [
    { key: 'protocol', header: 'Protocol' },
    {
      key: 'volume_usd',
      header: 'Volume (USD)',
      align: 'right',
      sortable: true,
      render: (item) => formatUSD(item.volume_usd),
    },
    {
      key: 'tx_count',
      header: 'Entries',
      align: 'right',
      render: (item) => item.tx_count.toLocaleString('en-US'),
    },
    {
      key: 'entry_types',
      header: 'Types',
      align: 'right',
      render: (item) => item.entry_types.join(', '),
    },
  ]

  // Columns for flow by wallet table
  const walletFlowColumns: Column<WalletFlow>[] = [
    { key: 'label', header: 'Wallet', render: (item) => item.label ?? item.wallet_id.slice(0, 8) },
    { key: 'chain', header: 'Chain' },
    {
      key: 'inflow_usd',
      header: 'Inflow',
      align: 'right',
      render: (item) => (
        <span className="text-green-600">{formatUSD(item.inflow_usd)}</span>
      ),
    },
    {
      key: 'outflow_usd',
      header: 'Outflow',
      align: 'right',
      render: (item) => (
        <span className="text-red-500">{formatUSD(item.outflow_usd)}</span>
      ),
    },
    {
      key: 'net_usd',
      header: 'Net',
      align: 'right',
      render: (item) => (
        <span className={item.net_usd >= 0 ? 'text-green-600' : 'text-red-500'}>
          {item.net_usd >= 0 ? '+' : ''}{formatUSD(item.net_usd)}
        </span>
      ),
    },
    {
      key: 'tx_count',
      header: 'Entries',
      align: 'right',
      sortable: true,
      render: (item) => item.tx_count.toLocaleString('en-US'),
    },
  ]

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-sm text-gray-500 mt-1">Management dashboard — portfolio and accounting overview</p>
        </div>
        <div className="flex items-center gap-3">
          {repriceResult && (
            <span className={`text-xs ${repriceResult.startsWith('Error') ? 'text-red-500' : 'text-green-600'}`}>
              {repriceResult}
            </span>
          )}
          <button
            onClick={handleReprice}
            disabled={repricing}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 rounded-lg transition-colors"
          >
            {repricing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <DollarSign className="w-4 h-4" />}
            {repricing ? 'Fetching Prices...' : 'Fetch Prices'}
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <FilterBar onReset={handleReset}>
        <DateRangePicker
          dateFrom={dateFrom}
          dateTo={dateTo}
          onDateFromChange={setDateFrom}
          onDateToChange={setDateTo}
        />
        <WalletSelector
          value={walletId}
          onChange={setWalletId}
          wallets={walletOptions}
        />
        <ChainSelector value={chain} onChange={setChain} />
        <GranularitySelector value={granularity} onChange={handleGranularityChange} />
      </FilterBar>

      {/* KPI Cards — Row 1: Financial */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          label="Total Inflow"
          value={kpi ? formatUSD(kpi.total_inflow_usd) : '—'}
          icon={<TrendingUp className="w-5 h-5" />}
          color="#22c55e"
        />
        <KPICard
          label="Total Outflow"
          value={kpi ? formatUSD(Math.abs(kpi.total_outflow_usd)) : '—'}
          icon={<TrendingDown className="w-5 h-5" />}
          color="#ef4444"
        />
        <KPICard
          label="Net Flow"
          value={kpi ? formatUSD(kpi.net_usd) : '—'}
          icon={<ArrowRightLeft className="w-5 h-5" />}
          color={kpi && kpi.net_usd >= 0 ? '#22c55e' : '#ef4444'}
        />
        <KPICard
          label="Unique Tokens"
          value={kpi ? kpi.unique_tokens.toLocaleString('en-US') : '—'}
          icon={<Coins className="w-5 h-5" />}
          color="#3b82f6"
        />
      </div>

      {/* KPI Cards — Row 2: Activity */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          label="Journal Entries"
          value={kpi ? kpi.total_entries.toLocaleString('en-US') : '—'}
          icon={<Hash className="w-5 h-5" />}
          color="#8b5cf6"
        />
        <KPICard
          label="Transactions"
          value={kpi ? kpi.total_txs.toLocaleString('en-US') : '—'}
          icon={<Layers className="w-5 h-5" />}
          color="#6366f1"
        />
        <KPICard
          label="Protocols"
          value={kpi ? kpi.unique_protocols.toLocaleString('en-US') : '—'}
          icon={<ArrowRightLeft className="w-5 h-5" />}
          color="#0ea5e9"
        />
        <KPICard
          label="Wallets"
          value={String(walletsData?.total ?? 0)}
          icon={<Coins className="w-5 h-5" />}
          color="#14b8a6"
        />
      </div>

      {/* CashFlow + Composition */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          {cashFlowQ.isLoading ? (
            <SectionSkeleton />
          ) : cashFlowQ.isError ? (
            <SectionError onRetry={() => cashFlowQ.refetch()} />
          ) : (
            <CashFlowChart data={cashFlowQ.data ?? []} title="Cash Flow" onBarClick={(period) => navigate(`/journal?date_from=${period}&date_to=${period}`)} />
          )}
        </div>

        <div>
          {compositionQ.isLoading ? (
            <SectionSkeleton />
          ) : compositionQ.isError ? (
            <SectionError onRetry={() => compositionQ.refetch()} />
          ) : (
            <CompositionDonut data={compositionQ.data ?? []} title="Portfolio Composition" />
          )}
        </div>
      </div>

      {/* Income/Expense + EntryType */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          {incomeExpenseQ.isLoading ? (
            <SectionSkeleton />
          ) : incomeExpenseQ.isError ? (
            <SectionError onRetry={() => incomeExpenseQ.refetch()} />
          ) : (
            <IncomeExpenseChart data={incomeExpenseQ.data ?? []} title="Income vs Expense" />
          )}
        </div>

        <div>
          {entryTypesQ.isLoading ? (
            <SectionSkeleton />
          ) : entryTypesQ.isError ? (
            <SectionError onRetry={() => entryTypesQ.refetch()} />
          ) : (
            <EntryTypeBar data={entryTypesQ.data ?? []} title="Entry Type Breakdown" onBarClick={(entryType) => navigate(`/journal?entry_type=${entryType}`)} />
          )}
        </div>
      </div>

      {/* Income/Expense Entry Count (supplementary) */}
      {incomeExpenseQ.data && incomeExpenseQ.data.length > 0 && (
        <IncomeExpenseCountChart data={incomeExpenseQ.data} />
      )}

      {/* Top Symbols Table */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Top Symbols by Volume</h3>
        {topSymbolsQ.isLoading ? (
          <div className="animate-pulse h-32 bg-gray-100 rounded" />
        ) : topSymbolsQ.isError ? (
          <div className="flex items-center gap-2 text-red-500 text-sm">
            <AlertCircle className="w-4 h-4" />
            Failed to load
            <button onClick={() => topSymbolsQ.refetch()} className="underline">Retry</button>
          </div>
        ) : (
          <DataTable
            columns={symbolColumns}
            data={topSymbolsQ.data ?? []}
            rowKey={(item) => item.symbol ?? 'unknown'}
            emptyMessage="No symbol data available"
            onRowClick={(item) => item.symbol && navigate(`/journal?symbol=${item.symbol}`)}
          />
        )}
      </div>

      {/* Top Protocols + Flow by Wallet */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Top Protocols</h3>
          {topProtocolsQ.isLoading ? (
            <div className="animate-pulse h-32 bg-gray-100 rounded" />
          ) : topProtocolsQ.isError ? (
            <div className="flex items-center gap-2 text-red-500 text-sm">
              <AlertCircle className="w-4 h-4" />
              Failed to load
              <button onClick={() => topProtocolsQ.refetch()} className="underline">Retry</button>
            </div>
          ) : (
            <DataTable
              columns={protocolColumns}
              data={topProtocolsQ.data ?? []}
              rowKey={(item) => item.protocol ?? 'unknown'}
              emptyMessage="No protocol data available"
            />
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Flow by Wallet</h3>
          {flowByWalletQ.isLoading ? (
            <div className="animate-pulse h-32 bg-gray-100 rounded" />
          ) : flowByWalletQ.isError ? (
            <div className="flex items-center gap-2 text-red-500 text-sm">
              <AlertCircle className="w-4 h-4" />
              Failed to load
              <button onClick={() => flowByWalletQ.refetch()} className="underline">Retry</button>
            </div>
          ) : (
            <DataTable
              columns={walletFlowColumns}
              data={flowByWalletQ.data ?? []}
              rowKey={(item) => item.wallet_id}
              emptyMessage="No wallet flow data available"
            />
          )}
        </div>
      </div>

      {/* Activity Heatmap */}
      <div>
        {activityQ.isLoading ? (
          <SectionSkeleton />
        ) : activityQ.isError ? (
          <SectionError onRetry={() => activityQ.refetch()} />
        ) : (
          <ActivityHeatmap data={activityQ.data ?? []} title="Activity Heatmap" />
        )}
      </div>
    </div>
  )
}
