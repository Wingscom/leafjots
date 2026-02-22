import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { TrendingUp, TrendingDown, ArrowRightLeft, Coins, RefreshCw, AlertCircle } from 'lucide-react'
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
  const { data: walletsData } = useWallets()

  const walletOptions = (walletsData?.wallets ?? []).map((w) => ({
    id: w.id,
    label: w.label ?? w.address ?? w.id,
  }))

  const [dateFrom, setDateFrom] = useState<string | null>(null)
  const [dateTo, setDateTo] = useState<string | null>(null)
  const [walletId, setWalletId] = useState<string | null>(null)
  const [chain, setChain] = useState<string | null>(null)
  const [granularity, setGranularity] = useState('month')

  const handleReset = useCallback(() => {
    setDateFrom(null)
    setDateTo(null)
    setWalletId(null)
    setChain(null)
    setGranularity('month')
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

  const kpi = overviewQ.data?.kpi

  // Columns for top symbols table
  const symbolColumns: Column<SymbolVolume>[] = [
    { key: 'symbol', header: 'Symbol', sortable: true },
    {
      key: 'volume_usd',
      header: 'Volume (USD)',
      align: 'right',
      sortable: true,
      render: (item) => formatUSD(item.volume_usd),
    },
    {
      key: 'trade_count',
      header: 'Trades',
      align: 'right',
      sortable: true,
      render: (item) => item.trade_count.toLocaleString('en-US'),
    },
    {
      key: 'avg_trade_usd',
      header: 'Avg Trade',
      align: 'right',
      render: (item) => formatUSD(item.avg_trade_usd),
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
      key: 'entry_count',
      header: 'Entries',
      align: 'right',
      render: (item) => item.entry_count.toLocaleString('en-US'),
    },
    {
      key: 'unique_symbols',
      header: 'Symbols',
      align: 'right',
      render: (item) => item.unique_symbols.toString(),
    },
  ]

  // Columns for flow by wallet table
  const walletFlowColumns: Column<WalletFlow>[] = [
    { key: 'wallet_label', header: 'Wallet' },
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
  ]

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
        <p className="text-sm text-gray-500 mt-1">Management dashboard — portfolio and accounting overview</p>
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
        <GranularitySelector value={granularity} onChange={setGranularity} />
      </FilterBar>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          label="Total Inflow"
          value={kpi ? formatUSD(kpi.total_inflow_usd) : '—'}
          icon={<TrendingUp className="w-5 h-5" />}
          color="#22c55e"
        />
        <KPICard
          label="Total Outflow"
          value={kpi ? formatUSD(kpi.total_outflow_usd) : '—'}
          icon={<TrendingDown className="w-5 h-5" />}
          color="#ef4444"
        />
        <KPICard
          label="Net Flow"
          value={kpi ? formatUSD(kpi.net_flow_usd) : '—'}
          icon={<ArrowRightLeft className="w-5 h-5" />}
          color={kpi && kpi.net_flow_usd >= 0 ? '#22c55e' : '#ef4444'}
        />
        <KPICard
          label="Unique Tokens"
          value={kpi ? kpi.unique_symbols.toLocaleString('en-US') : '—'}
          icon={<Coins className="w-5 h-5" />}
          color="#3b82f6"
        />
      </div>

      {/* CashFlow + Composition */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CashFlow Chart */}
        <div>
          {cashFlowQ.isLoading ? (
            <SectionSkeleton />
          ) : cashFlowQ.isError ? (
            <SectionError onRetry={() => cashFlowQ.refetch()} />
          ) : (
            <CashFlowChart data={cashFlowQ.data ?? []} title="Cash Flow" onBarClick={(period) => navigate(`/journal?date_from=${period}&date_to=${period}`)} />
          )}
        </div>

        {/* Composition Donut */}
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
            rowKey={(item) => item.symbol}
            emptyMessage="No symbol data available"
            onRowClick={(item) => navigate(`/journal?symbol=${item.symbol}`)}
          />
        )}
      </div>

      {/* Top Protocols + Flow by Wallet */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Protocols */}
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
              rowKey={(item) => item.protocol}
              emptyMessage="No protocol data available"
            />
          )}
        </div>

        {/* Flow by Wallet */}
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
