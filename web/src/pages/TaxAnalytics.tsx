import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, TrendingUp, TrendingDown, BarChart2, DollarSign, AlertCircle, RefreshCw } from 'lucide-react'
import {
  useGainsOverTime,
  useGainsBySymbol,
  useHoldingDistribution,
  useWinnersLosers,
  useTaxBreakdown,
  useTaxByCategory,
  useUnrealized,
  useCostBasis,
} from '../hooks/useAnalytics'
import type {
  AnalyticsFilters,
  GainsBySymbol,
  TaxBreakdownPeriod,
  TaxByCategory,
  UnrealizedPosition,
  CostBasisItem,
} from '../api/analytics'
import {
  KPICard,
  GainsLossChart,
  HoldingDistribution,
  WinnersLosers,
} from '../components/charts'
import {
  FilterBar,
  DateRangePicker,
  SymbolInput,
  GranularitySelector,
} from '../components/filters'
import DataTable, { type Column } from '../components/DataTable'

function formatUSD(value: number): string {
  if (Math.abs(value) >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(2)}M`
  }
  if (Math.abs(value) >= 1_000) {
    return `$${(value / 1_000).toFixed(1)}k`
  }
  return `$${value.toLocaleString('en-US', { maximumFractionDigits: 2 })}`
}

function formatVND(value: number): string {
  return `₫${Math.round(value).toLocaleString('vi-VN')}`
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

export default function TaxAnalytics() {
  const navigate = useNavigate()

  const [dateFrom, setDateFrom] = useState<string | null>(null)
  const [dateTo, setDateTo] = useState<string | null>(null)
  const [symbol, setSymbol] = useState('')
  const [granularity, setGranularity] = useState('month')

  const handleReset = useCallback(() => {
    setDateFrom(null)
    setDateTo(null)
    setSymbol('')
    setGranularity('month')
  }, [])

  const filters: AnalyticsFilters = {
    ...(dateFrom ? { date_from: dateFrom } : {}),
    ...(dateTo ? { date_to: dateTo } : {}),
    ...(symbol ? { symbol } : {}),
    granularity,
  }

  const gainsOverTimeQ = useGainsOverTime(filters)
  const gainsBySymbolQ = useGainsBySymbol(filters)
  const holdingDistQ = useHoldingDistribution(filters)
  const winnersLosersQ = useWinnersLosers(filters)
  const taxBreakdownQ = useTaxBreakdown(filters)
  const taxByCategoryQ = useTaxByCategory(filters)
  const unrealizedQ = useUnrealized(filters)
  const costBasisQ = useCostBasis(filters)

  // Compute KPI values from gains-by-symbol data
  const gainsBySymbolData = gainsBySymbolQ.data ?? []
  const totalGains = gainsBySymbolData.reduce(
    (sum, s) => sum + (s.total_gain_usd > 0 ? s.total_gain_usd : 0),
    0
  )
  const totalLosses = gainsBySymbolData.reduce(
    (sum, s) => sum + (s.total_loss_usd < 0 ? s.total_loss_usd : 0),
    0
  )
  const netGain = totalGains + totalLosses

  // Tax due from breakdown
  const taxBreakdownData = taxBreakdownQ.data ?? []
  const taxDueVnd = taxBreakdownData.reduce((sum, p) => sum + p.total_tax_vnd, 0)

  // Columns for gains by symbol table
  const gainsBySymbolColumns: Column<GainsBySymbol>[] = [
    { key: 'symbol', header: 'Symbol', sortable: true },
    {
      key: 'total_gain_usd',
      header: 'Gains',
      align: 'right',
      sortable: true,
      render: (item) => (
        <span className="text-green-600">{formatUSD(item.total_gain_usd)}</span>
      ),
    },
    {
      key: 'total_loss_usd',
      header: 'Losses',
      align: 'right',
      sortable: true,
      render: (item) => (
        <span className="text-red-500">{formatUSD(item.total_loss_usd)}</span>
      ),
    },
    {
      key: 'net_gain_usd',
      header: 'Net',
      align: 'right',
      sortable: true,
      render: (item) => (
        <span className={item.net_gain_usd >= 0 ? 'text-green-600 font-medium' : 'text-red-500 font-medium'}>
          {item.net_gain_usd >= 0 ? '+' : ''}{formatUSD(item.net_gain_usd)}
        </span>
      ),
    },
    {
      key: 'avg_holding_days',
      header: 'Avg Hold',
      align: 'right',
      render: (item) => `${Math.round(item.avg_holding_days)}d`,
    },
    {
      key: 'lot_count',
      header: 'Lots',
      align: 'right',
      render: (item) => item.lot_count.toLocaleString('en-US'),
    },
  ]

  // Columns for tax breakdown table
  const taxBreakdownColumns: Column<TaxBreakdownPeriod>[] = [
    { key: 'period', header: 'Period' },
    {
      key: 'total_tax_vnd',
      header: 'Tax Due',
      align: 'right',
      render: (item) => (
        <span className="font-medium text-orange-600">{formatVND(item.total_tax_vnd)}</span>
      ),
    },
    {
      key: 'taxable_vnd',
      header: 'Taxable Value',
      align: 'right',
      render: (item) => formatVND(item.taxable_vnd),
    },
    {
      key: 'exempt_vnd',
      header: 'Exempt Value',
      align: 'right',
      render: (item) => formatVND(item.exempt_vnd),
    },
    {
      key: 'transfer_count',
      header: 'Transfers',
      align: 'right',
      render: (item) => item.transfer_count.toLocaleString('en-US'),
    },
  ]

  // Columns for tax by category table
  const taxByCategoryColumns: Column<TaxByCategory>[] = [
    { key: 'category', header: 'Category' },
    {
      key: 'total_tax_vnd',
      header: 'Tax (VND)',
      align: 'right',
      render: (item) => formatVND(item.total_tax_vnd),
    },
    {
      key: 'transfer_count',
      header: 'Transfers',
      align: 'right',
      render: (item) => item.transfer_count.toLocaleString('en-US'),
    },
    {
      key: 'volume_usd',
      header: 'Volume (USD)',
      align: 'right',
      render: (item) => formatUSD(item.volume_usd),
    },
  ]

  // Columns for unrealized P&L table
  const unrealizedColumns: Column<UnrealizedPosition>[] = [
    { key: 'symbol', header: 'Symbol', sortable: true },
    {
      key: 'total_quantity',
      header: 'Quantity',
      align: 'right',
      render: (item) => item.total_quantity.toLocaleString('en-US', { maximumFractionDigits: 6 }),
    },
    {
      key: 'cost_basis_usd',
      header: 'Cost Basis',
      align: 'right',
      sortable: true,
      render: (item) => formatUSD(item.cost_basis_usd),
    },
    {
      key: 'current_value_usd',
      header: 'Current Value',
      align: 'right',
      render: (item) =>
        item.current_value_usd != null ? formatUSD(item.current_value_usd) : '—',
    },
    {
      key: 'unrealized_gain_usd',
      header: 'Unrealized P&L',
      align: 'right',
      render: (item) => {
        if (item.unrealized_gain_usd == null) return '—'
        return (
          <span className={item.unrealized_gain_usd >= 0 ? 'text-green-600' : 'text-red-500'}>
            {item.unrealized_gain_usd >= 0 ? '+' : ''}{formatUSD(item.unrealized_gain_usd)}
          </span>
        )
      },
    },
    {
      key: 'lot_count',
      header: 'Lots',
      align: 'right',
      render: (item) => item.lot_count.toString(),
    },
  ]

  // Columns for cost basis table
  const costBasisColumns: Column<CostBasisItem>[] = [
    { key: 'symbol', header: 'Symbol', sortable: true },
    {
      key: 'buy_date',
      header: 'Buy Date',
      render: (item) => item.buy_date.slice(0, 10),
    },
    {
      key: 'quantity',
      header: 'Quantity',
      align: 'right',
      render: (item) => item.quantity.toLocaleString('en-US', { maximumFractionDigits: 6 }),
    },
    {
      key: 'cost_basis_per_unit_usd',
      header: 'Cost/Unit',
      align: 'right',
      render: (item) => formatUSD(item.cost_basis_per_unit_usd),
    },
    {
      key: 'total_cost_usd',
      header: 'Total Cost',
      align: 'right',
      sortable: true,
      render: (item) => formatUSD(item.total_cost_usd),
    },
  ]

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tax Analytics</h1>
          <p className="text-sm text-gray-500 mt-1">Capital gains, realized P&L, and Vietnamese tax obligations</p>
        </div>
        <button
          onClick={() => navigate('/tax')}
          className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Tax
        </button>
      </div>

      {/* Filter Bar */}
      <FilterBar onReset={handleReset}>
        <DateRangePicker
          dateFrom={dateFrom}
          dateTo={dateTo}
          onDateFromChange={setDateFrom}
          onDateToChange={setDateTo}
        />
        <SymbolInput value={symbol} onChange={setSymbol} />
        <GranularitySelector value={granularity} onChange={setGranularity} />
      </FilterBar>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          label="Total Gains"
          value={gainsBySymbolQ.isLoading ? '—' : formatUSD(totalGains)}
          icon={<TrendingUp className="w-5 h-5" />}
          color="#22c55e"
        />
        <KPICard
          label="Total Losses"
          value={gainsBySymbolQ.isLoading ? '—' : formatUSD(Math.abs(totalLosses))}
          icon={<TrendingDown className="w-5 h-5" />}
          color="#ef4444"
        />
        <KPICard
          label="Net Gain"
          value={gainsBySymbolQ.isLoading ? '—' : formatUSD(netGain)}
          icon={<BarChart2 className="w-5 h-5" />}
          color={netGain >= 0 ? '#22c55e' : '#ef4444'}
        />
        <KPICard
          label="Tax Due (VND)"
          value={taxBreakdownQ.isLoading ? '—' : formatVND(taxDueVnd)}
          icon={<DollarSign className="w-5 h-5" />}
          color="#f97316"
        />
      </div>

      {/* Gains/Loss Chart */}
      <div>
        {gainsOverTimeQ.isLoading ? (
          <SectionSkeleton />
        ) : gainsOverTimeQ.isError ? (
          <SectionError onRetry={() => gainsOverTimeQ.refetch()} />
        ) : (
          <GainsLossChart data={gainsOverTimeQ.data ?? []} title="Realized Gains & Losses Over Time" />
        )}
      </div>

      {/* Gains by Symbol + Holding Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Gains by Symbol */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Gains by Symbol</h3>
          {gainsBySymbolQ.isLoading ? (
            <div className="animate-pulse h-32 bg-gray-100 rounded" />
          ) : gainsBySymbolQ.isError ? (
            <div className="flex items-center gap-2 text-red-500 text-sm">
              <AlertCircle className="w-4 h-4" />
              Failed to load
              <button onClick={() => gainsBySymbolQ.refetch()} className="underline">Retry</button>
            </div>
          ) : (
            <DataTable
              columns={gainsBySymbolColumns}
              data={gainsBySymbolData}
              rowKey={(item) => item.symbol}
              emptyMessage="No gains data available"
              onRowClick={(item) => navigate(`/journal?symbol=${item.symbol}`)}
            />
          )}
        </div>

        {/* Holding Distribution */}
        <div>
          {holdingDistQ.isLoading ? (
            <SectionSkeleton />
          ) : holdingDistQ.isError ? (
            <SectionError onRetry={() => holdingDistQ.refetch()} />
          ) : (
            <HoldingDistribution data={holdingDistQ.data ?? []} title="Holding Period Distribution" />
          )}
        </div>
      </div>

      {/* Winners & Losers */}
      <div>
        {winnersLosersQ.isLoading ? (
          <SectionSkeleton />
        ) : winnersLosersQ.isError ? (
          <SectionError onRetry={() => winnersLosersQ.refetch()} />
        ) : winnersLosersQ.data ? (
          <WinnersLosers data={winnersLosersQ.data} title="Winners & Losers (Top 10)" />
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 p-5 text-center text-gray-400 text-sm h-24 flex items-center justify-center">
            No data available
          </div>
        )}
      </div>

      {/* Tax Breakdown + Tax by Category */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tax Breakdown by Period */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Tax Breakdown by Period</h3>
          {taxBreakdownQ.isLoading ? (
            <div className="animate-pulse h-32 bg-gray-100 rounded" />
          ) : taxBreakdownQ.isError ? (
            <div className="flex items-center gap-2 text-red-500 text-sm">
              <AlertCircle className="w-4 h-4" />
              Failed to load
              <button onClick={() => taxBreakdownQ.refetch()} className="underline">Retry</button>
            </div>
          ) : (
            <DataTable
              columns={taxBreakdownColumns}
              data={taxBreakdownData}
              rowKey={(item) => item.period}
              emptyMessage="No tax breakdown data available"
            />
          )}
        </div>

        {/* Tax by Category */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Tax by Category</h3>
          {taxByCategoryQ.isLoading ? (
            <div className="animate-pulse h-32 bg-gray-100 rounded" />
          ) : taxByCategoryQ.isError ? (
            <div className="flex items-center gap-2 text-red-500 text-sm">
              <AlertCircle className="w-4 h-4" />
              Failed to load
              <button onClick={() => taxByCategoryQ.refetch()} className="underline">Retry</button>
            </div>
          ) : (
            <DataTable
              columns={taxByCategoryColumns}
              data={taxByCategoryQ.data ?? []}
              rowKey={(item) => item.category}
              emptyMessage="No category data available"
            />
          )}
        </div>
      </div>

      {/* Unrealized P&L Table */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Unrealized P&L (Open Lots)</h3>
        {unrealizedQ.isLoading ? (
          <div className="animate-pulse h-32 bg-gray-100 rounded" />
        ) : unrealizedQ.isError ? (
          <div className="flex items-center gap-2 text-red-500 text-sm">
            <AlertCircle className="w-4 h-4" />
            Failed to load
            <button onClick={() => unrealizedQ.refetch()} className="underline">Retry</button>
          </div>
        ) : (
          <DataTable
            columns={unrealizedColumns}
            data={unrealizedQ.data ?? []}
            rowKey={(item) => item.symbol}
            emptyMessage="No open positions"
          />
        )}
      </div>

      {/* Cost Basis Summary Table */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Cost Basis Detail</h3>
        {costBasisQ.isLoading ? (
          <div className="animate-pulse h-32 bg-gray-100 rounded" />
        ) : costBasisQ.isError ? (
          <div className="flex items-center gap-2 text-red-500 text-sm">
            <AlertCircle className="w-4 h-4" />
            Failed to load
            <button onClick={() => costBasisQ.refetch()} className="underline">Retry</button>
          </div>
        ) : (
          <DataTable
            columns={costBasisColumns}
            data={costBasisQ.data ?? []}
            rowKey={(item) => `${item.symbol}-${item.buy_date}`}
            emptyMessage="No cost basis data"
          />
        )}
      </div>
    </div>
  )
}
