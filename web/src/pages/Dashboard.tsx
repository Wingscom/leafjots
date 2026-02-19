import { useNavigate } from 'react-router-dom'
import { Wallet, ArrowLeftRight, CheckCircle, AlertTriangle, Plus, Upload, Play, FileSpreadsheet, Calculator } from 'lucide-react'
import { useWallets } from '../hooks/useWallets'
import { useTransactions } from '../hooks/useTransactions'
import { useParseStats } from '../hooks/useParser'
import { useEntities } from '../hooks/useEntities'
import { useEntity } from '../context/EntityContext'

export default function Dashboard() {
  const navigate = useNavigate()
  const { entityId } = useEntity()
  const { data: entitiesData } = useEntities()
  const selectedEntity = entitiesData?.entities.find((e) => e.id === entityId)

  const { data: walletData } = useWallets()
  const { data: txData } = useTransactions({ limit: 1 })
  const { data: parseStats } = useParseStats()
  const walletCount = walletData?.total ?? 0
  const txCount = txData?.total ?? 0

  const parsedPct = parseStats && parseStats.total > 0
    ? `${Math.round((parseStats.parsed / parseStats.total) * 100)}%`
    : '0%'
  const errorCount = parseStats?.errors ?? 0

  // Empty state: no entity or no wallets
  if (!entityId || walletCount === 0) {
    return <OnboardingView hasEntity={!!entityId} entityName={selectedEntity?.name} navigate={navigate} />
  }

  const stats = [
    { label: 'Wallets tracked', value: String(walletCount), icon: Wallet, color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Transactions loaded', value: txCount.toLocaleString(), icon: ArrowLeftRight, color: 'text-purple-600', bg: 'bg-purple-50' },
    { label: 'Parsed', value: parsedPct, icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50' },
    { label: 'Errors', value: String(errorCount), icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-50' },
  ]

  return (
    <div>
      <div className="flex items-baseline gap-3 mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
        {selectedEntity && (
          <span className="text-lg text-gray-500">
            — {selectedEntity.name}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
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

      {/* Quick Actions */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-8">
        <h3 className="font-semibold text-gray-900 mb-3">Quick Actions</h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => navigate('/wallets')}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-50 text-blue-700 text-sm font-medium hover:bg-blue-100 transition-colors"
          >
            <Plus className="w-4 h-4" /> Add Wallet
          </button>
          <button
            onClick={() => navigate('/imports')}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-50 text-orange-700 text-sm font-medium hover:bg-orange-100 transition-colors"
          >
            <Upload className="w-4 h-4" /> Import Binance CSV
          </button>
          <button
            onClick={() => navigate('/tax')}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-purple-50 text-purple-700 text-sm font-medium hover:bg-purple-100 transition-colors"
          >
            <Calculator className="w-4 h-4" /> Calculate Tax
          </button>
          <button
            onClick={() => navigate('/reports')}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-50 text-green-700 text-sm font-medium hover:bg-green-100 transition-colors"
          >
            <FileSpreadsheet className="w-4 h-4" /> Generate Report
          </button>
        </div>
      </div>

      {/* Protocol Coverage */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-8">
        <h3 className="font-semibold text-gray-900 mb-3">Protocol Coverage</h3>
        <div className="flex flex-wrap gap-2">
          {[
            { name: 'Aave V3', color: 'bg-purple-100 text-purple-700' },
            { name: 'Uniswap V3', color: 'bg-pink-100 text-pink-700' },
            { name: 'Curve', color: 'bg-blue-100 text-blue-700' },
            { name: 'PancakeSwap', color: 'bg-yellow-100 text-yellow-700' },
            { name: 'Morpho Blue', color: 'bg-indigo-100 text-indigo-700' },
            { name: 'MetaMorpho', color: 'bg-indigo-50 text-indigo-600' },
            { name: 'Lido', color: 'bg-cyan-100 text-cyan-700' },
            { name: 'Pendle', color: 'bg-emerald-100 text-emerald-700' },
            { name: 'Binance CEX', color: 'bg-orange-100 text-orange-700' },
            { name: 'Generic Swap', color: 'bg-gray-100 text-gray-600' },
            { name: 'Generic EVM', color: 'bg-gray-50 text-gray-500' },
          ].map(p => (
            <span key={p.name} className={`px-2.5 py-1 rounded-full text-xs font-medium ${p.color}`}>
              {p.name}
            </span>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
        <p className="text-gray-400 text-lg mb-2">LeafJots v0.1.0</p>
        <p className="text-gray-500 text-sm">
          11 parsers active — Morpho, Lido, Pendle, Aave, Uniswap, Curve, PancakeSwap, Binance CEX.
        </p>
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
