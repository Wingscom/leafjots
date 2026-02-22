import { useNavigate, Link } from 'react-router-dom'
import {
  Wallet,
  BookOpen,
  CheckCircle,
  AlertTriangle,
  Plus,
  Upload,
  Play,
  FileSpreadsheet,
  Calculator,
  BarChart2,
  CircleDot,
  AlertCircle,
  ExternalLink,
} from 'lucide-react'
import { useWallets } from '../hooks/useWallets'
import { useParseStats } from '../hooks/useParser'
import { useEntities } from '../hooks/useEntities'
import { useEntity } from '../context/EntityContext'
import { useOverview, useComposition } from '../hooks/useAnalytics'
import { useJournalEntries, useUnbalancedEntries } from '../hooks/useJournal'
import { useErrorSummary } from '../hooks/useErrors'

// Entry type badge colors
const ENTRY_TYPE_COLORS: Record<string, string> = {
  swap: 'bg-purple-100 text-purple-700',
  transfer: 'bg-blue-100 text-blue-700',
  deposit: 'bg-green-100 text-green-700',
  withdrawal: 'bg-orange-100 text-orange-700',
  borrow: 'bg-red-100 text-red-700',
  repay: 'bg-emerald-100 text-emerald-700',
  gas: 'bg-gray-100 text-gray-600',
  yield: 'bg-teal-100 text-teal-700',
  approve: 'bg-slate-100 text-slate-600',
  liquidation: 'bg-rose-100 text-rose-700',
}

function entryTypeBadgeClass(entryType: string): string {
  return ENTRY_TYPE_COLORS[entryType.toLowerCase()] ?? 'bg-gray-100 text-gray-600'
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffHrs = diffMs / (1000 * 60 * 60)

  if (diffHrs < 1) {
    const mins = Math.floor(diffMs / (1000 * 60))
    return `${mins}m ago`
  }
  if (diffHrs < 24) {
    return `${Math.floor(diffHrs)}h ago`
  }
  if (diffHrs < 24 * 7) {
    return `${Math.floor(diffHrs / 24)}d ago`
  }
  return d.toLocaleDateString()
}

function formatUsd(v: number | null | undefined): string {
  if (v === null || v === undefined) return '--'
  if (Math.abs(v) < 0.01) return '$0.00'
  return `$${Math.abs(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatQuantity(v: number): string {
  if (Math.abs(v) < 0.0001) return '0'
  if (Math.abs(v) < 1) return v.toFixed(6)
  if (Math.abs(v) < 1000) return v.toFixed(4)
  return v.toLocaleString(undefined, { maximumFractionDigits: 2 })
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { entityId } = useEntity()
  const { data: entitiesData } = useEntities()
  const selectedEntity = entitiesData?.entities.find((e) => e.id === entityId)

  const { data: walletData } = useWallets()
  const { data: parseStats } = useParseStats()
  const { data: overviewData } = useOverview({})
  const { data: compositionData } = useComposition({})
  const { data: recentJournal } = useJournalEntries({ limit: 5 })
  const { data: unbalancedData } = useUnbalancedEntries()
  const { data: errorSummary } = useErrorSummary()

  const walletCount = walletData?.total ?? 0

  // Empty state: no entity or no wallets
  if (!entityId || walletCount === 0) {
    return <OnboardingView hasEntity={!!entityId} entityName={selectedEntity?.name} navigate={navigate} />
  }

  // Status card data
  const totalEntries = overviewData?.kpi.total_entries ?? 0
  const parsedPct = parseStats && parseStats.total > 0
    ? Math.round((parseStats.parsed / parseStats.total) * 100)
    : 0

  // Count null-price splits from composition (items with 0 USD value but non-zero qty)
  const missingPriceCount = (compositionData ?? []).filter(
    (c) => c.balance_qty !== 0 && c.balance_usd === 0
  ).length

  const stats = [
    {
      label: 'Wallets Tracked',
      value: String(walletCount),
      icon: Wallet,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
    },
    {
      label: 'Journal Entries',
      value: totalEntries.toLocaleString(),
      icon: BookOpen,
      color: 'text-purple-600',
      bg: 'bg-purple-50',
    },
    {
      label: 'Parse Coverage',
      value: `${parsedPct}%`,
      icon: CheckCircle,
      color: parsedPct >= 90 ? 'text-green-600' : parsedPct >= 70 ? 'text-yellow-600' : 'text-red-600',
      bg: parsedPct >= 90 ? 'bg-green-50' : parsedPct >= 70 ? 'bg-yellow-50' : 'bg-red-50',
    },
    {
      label: 'Missing Prices',
      value: String(missingPriceCount),
      icon: AlertTriangle,
      color: missingPriceCount === 0 ? 'text-green-600' : 'text-amber-600',
      bg: missingPriceCount === 0 ? 'bg-green-50' : 'bg-amber-50',
    },
  ]

  // Top holdings from composition - sorted by USD value, top 5
  const topHoldings = [...(compositionData ?? [])]
    .filter((c) => c.account_type === 'ASSET' && c.balance_qty !== 0)
    .sort((a, b) => Math.abs(b.balance_usd) - Math.abs(a.balance_usd))
    .slice(0, 5)

  // Recent journal entries
  const recentEntries = recentJournal?.entries ?? []

  // Data health
  const unbalancedCount = Array.isArray(unbalancedData) ? unbalancedData.length : (unbalancedData?.total ?? 0)
  const parseErrorCount = errorSummary?.unresolved ?? parseStats?.errors ?? 0

  const healthItems = [
    {
      label: 'Unbalanced entries',
      count: unbalancedCount,
      link: '/journal?filter=unbalanced',
    },
    {
      label: 'Missing prices',
      count: missingPriceCount,
      link: '/journal',
    },
    {
      label: 'Parse errors',
      count: parseErrorCount,
      link: '/errors',
    },
  ]

  return (
    <div>
      {/* Header */}
      <div className="flex items-baseline gap-3 mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
        {selectedEntity && (
          <span className="text-lg text-gray-500">
            — {selectedEntity.name}
          </span>
        )}
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {stats.map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-gray-500">{label}</span>
              <div className={`${bg} p-2 rounded-lg`}>
                <Icon className={`w-4 h-4 ${color}`} />
              </div>
            </div>
            <p className="text-2xl font-bold text-gray-900">{value}</p>
          </div>
        ))}
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left column - 3/5 width */}
        <div className="lg:col-span-3 space-y-6">
          {/* Recent Activity */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">Recent Activity</h3>
              <Link
                to="/journal"
                className="text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
              >
                View all <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
            {recentEntries.length === 0 ? (
              <p className="text-sm text-gray-400 py-4 text-center">No journal entries yet</p>
            ) : (
              <div className="space-y-3">
                {recentEntries.map((entry) => (
                  <Link
                    key={entry.id}
                    to={`/journal?selected=${entry.id}`}
                    className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-gray-50 transition-colors group"
                  >
                    <div className="shrink-0">
                      <CircleDot className="w-4 h-4 text-gray-400 group-hover:text-blue-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${entryTypeBadgeClass(entry.entry_type)}`}>
                          {entry.entry_type}
                        </span>
                        <span className="text-xs text-gray-400">{formatDate(entry.timestamp)}</span>
                      </div>
                      <p className="text-sm text-gray-700 truncate">{entry.description || 'No description'}</p>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Top Holdings */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">Top Holdings</h3>
              <Link
                to="/accounts"
                className="text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
              >
                All accounts <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
            {topHoldings.length === 0 ? (
              <p className="text-sm text-gray-400 py-4 text-center">No holdings data</p>
            ) : (
              <div className="space-y-2">
                {topHoldings.map((item, i) => (
                  <div
                    key={`${item.symbol}-${item.subtype}-${i}`}
                    className="flex items-center justify-between p-2.5 rounded-lg hover:bg-gray-50"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-100 to-purple-100 flex items-center justify-center">
                        <span className="text-xs font-bold text-blue-700">
                          {(item.symbol ?? '?').slice(0, 3).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{item.symbol ?? 'Unknown'}</p>
                        <p className="text-xs text-gray-400">{formatQuantity(item.balance_qty)}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-gray-900">{formatUsd(item.balance_usd)}</p>
                      {item.protocol && (
                        <p className="text-xs text-gray-400">{item.protocol}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right column - 2/5 width */}
        <div className="lg:col-span-2 space-y-6">
          {/* Quick Actions */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-3">Quick Actions</h3>
            <div className="space-y-2">
              <button
                onClick={() => navigate('/wallets')}
                className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg bg-blue-50 text-blue-700 text-sm font-medium hover:bg-blue-100 transition-colors text-left"
              >
                <Plus className="w-4 h-4 shrink-0" />
                Add Wallet
              </button>
              <button
                onClick={() => navigate('/imports')}
                className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg bg-orange-50 text-orange-700 text-sm font-medium hover:bg-orange-100 transition-colors text-left"
              >
                <Upload className="w-4 h-4 shrink-0" />
                Import Binance CSV
              </button>
              <button
                onClick={() => navigate('/tax')}
                className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg bg-purple-50 text-purple-700 text-sm font-medium hover:bg-purple-100 transition-colors text-left"
              >
                <Calculator className="w-4 h-4 shrink-0" />
                Calculate Tax
              </button>
              <button
                onClick={() => navigate('/reports')}
                className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg bg-green-50 text-green-700 text-sm font-medium hover:bg-green-100 transition-colors text-left"
              >
                <FileSpreadsheet className="w-4 h-4 shrink-0" />
                Generate Report
              </button>
              <button
                onClick={() => navigate('/analytics')}
                className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg bg-indigo-50 text-indigo-700 text-sm font-medium hover:bg-indigo-100 transition-colors text-left"
              >
                <BarChart2 className="w-4 h-4 shrink-0" />
                View Analytics
              </button>
            </div>
          </div>

          {/* Data Health */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-3">Data Health</h3>
            <div className="space-y-3">
              {healthItems.map((item) => (
                <Link
                  key={item.label}
                  to={item.link}
                  className="flex items-center justify-between p-2.5 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <div
                      className={`w-2 h-2 rounded-full shrink-0 ${
                        item.count === 0 ? 'bg-green-500' : 'bg-red-500'
                      }`}
                    />
                    <span className="text-sm text-gray-700">{item.label}</span>
                  </div>
                  <span
                    className={`text-sm font-semibold ${
                      item.count === 0 ? 'text-green-600' : 'text-red-600'
                    }`}
                  >
                    {item.count}
                  </span>
                </Link>
              ))}
            </div>
            {/* Overall health indicator */}
            {(() => {
              const totalIssues = unbalancedCount + missingPriceCount + parseErrorCount
              return (
                <div className={`mt-4 pt-3 border-t border-gray-100 flex items-center gap-2 ${
                  totalIssues === 0 ? 'text-green-600' : 'text-amber-600'
                }`}>
                  {totalIssues === 0 ? (
                    <>
                      <CheckCircle className="w-4 h-4" />
                      <span className="text-sm font-medium">All clear</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="w-4 h-4" />
                      <span className="text-sm font-medium">{totalIssues} issue{totalIssues !== 1 ? 's' : ''} need attention</span>
                    </>
                  )}
                </div>
              )
            })()}
          </div>
        </div>
      </div>
    </div>
  )
}


function OnboardingView({ hasEntity, entityName, navigate }: { hasEntity: boolean; entityName?: string; navigate: (path: string) => void }) {
  const steps = [
    {
      num: 1,
      title: 'Create an Entity',
      desc: 'An entity represents a person or organization for accounting.',
      done: hasEntity,
      action: hasEntity ? undefined : () => navigate('/entities'),
      actionLabel: 'Create Entity',
    },
    {
      num: 2,
      title: 'Add a Wallet',
      desc: 'Add your Ethereum wallet address or import Binance CSV data.',
      done: false,
      action: hasEntity ? () => navigate('/wallets') : undefined,
      actionLabel: 'Add Wallet',
    },
    {
      num: 3,
      title: 'Sync & Parse',
      desc: 'Load transactions from the blockchain and parse them into journal entries.',
      done: false,
    },
    {
      num: 4,
      title: 'Calculate Tax & Export',
      desc: 'Run FIFO matching, compute capital gains, and export reports.',
      done: false,
    },
  ]

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-2">Welcome to LeafJots</h2>
      <p className="text-gray-500 mb-8">Automated DeFi accounting — parse, classify, and report your on-chain transactions. Follow these steps to get started.</p>

      {hasEntity && entityName && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-6 flex items-center gap-3">
          <CheckCircle className="w-5 h-5 text-green-600 shrink-0" />
          <div>
            <p className="font-medium text-green-800">Entity: {entityName}</p>
            <p className="text-sm text-green-600">Now add a wallet to start loading transactions.</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        {steps.map((step) => (
          <div
            key={step.num}
            className={`bg-white rounded-xl border p-5 ${step.done ? 'border-green-200 bg-green-50/30' : 'border-gray-200'}`}
          >
            <div className="flex items-start gap-3">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0 ${step.done ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                {step.done ? <CheckCircle className="w-4 h-4" /> : step.num}
              </div>
              <div className="flex-1">
                <h3 className={`font-semibold mb-1 ${step.done ? 'text-green-700' : 'text-gray-900'}`}>
                  {step.title}
                </h3>
                <p className="text-sm text-gray-500 mb-3">{step.desc}</p>
                {step.action && (
                  <button
                    onClick={step.action}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
                  >
                    <Play className="w-3.5 h-3.5" />
                    {step.actionLabel}
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Supported Protocols */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="font-semibold text-gray-900 mb-3">Supported Protocols</h3>
        <div className="flex flex-wrap gap-2">
          {[
            'Aave V3', 'Uniswap V3', 'Curve', 'PancakeSwap',
            'Morpho Blue', 'MetaMorpho', 'Lido', 'Pendle',
            'Binance (CSV)', 'Generic Swap', 'Generic EVM',
          ].map(name => (
            <span key={name} className="px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
              {name}
            </span>
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-3">7 EVM chains: Ethereum, Arbitrum, Optimism, Polygon, Base, BSC, Avalanche</p>
      </div>
    </div>
  )
}
