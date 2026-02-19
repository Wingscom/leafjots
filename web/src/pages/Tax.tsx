import { useState } from 'react'
import { Calculator, TrendingUp, TrendingDown, ShieldCheck, ArrowUpDown } from 'lucide-react'
import { useCalculateTax, useRealizedGains, useOpenLots, useTaxSummary } from '../hooks/useTax'
import type { TaxCalculateResponse } from '../api/tax'

type TabId = 'gains' | 'lots' | 'transfers'

export default function Tax() {
  const [startDate, setStartDate] = useState('2025-01-01')
  const [endDate, setEndDate] = useState('2025-12-31')
  const [activeTab, setActiveTab] = useState<TabId>('gains')
  const [calcResult, setCalcResult] = useState<TaxCalculateResponse | null>(null)

  const calculateMutation = useCalculateTax()
  const { data: savedGains } = useRealizedGains()
  const { data: savedLots } = useOpenLots()
  const { data: savedSummary } = useTaxSummary()

  const summary = calcResult?.summary ?? savedSummary
  const closedLots = calcResult?.closed_lots ?? savedGains ?? []
  const openLots = calcResult?.open_lots ?? savedLots ?? []
  const transfers = calcResult?.taxable_transfers ?? []

  const handleCalculate = () => {
    calculateMutation.mutate(
      { start_date: startDate, end_date: endDate },
      { onSuccess: (data) => setCalcResult(data) }
    )
  }

  const tabs: { id: TabId; label: string; count: number }[] = [
    { id: 'gains', label: 'Realized Gains', count: closedLots.length },
    { id: 'lots', label: 'Open Lots', count: openLots.length },
    { id: 'transfers', label: 'Taxable Transfers', count: transfers.length },
  ]

  const fmtUsd = (v: number) => `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  const fmtVnd = (v: number) => `${v.toLocaleString()} VND`

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Tax Calculator</h2>

      {/* Controls */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 flex items-end gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Start Date</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <button
          onClick={handleCalculate}
          disabled={calculateMutation.isPending}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
        >
          <Calculator className="w-4 h-4" />
          {calculateMutation.isPending ? 'Calculating...' : 'Calculate Tax'}
        </button>
        {calculateMutation.isError && (
          <span className="text-red-500 text-sm">{String(calculateMutation.error)}</span>
        )}
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <SummaryCard
            label="Total Realized Gains"
            value={fmtUsd(summary.total_realized_gain_usd)}
            icon={summary.total_realized_gain_usd >= 0 ? TrendingUp : TrendingDown}
            color={summary.total_realized_gain_usd >= 0 ? 'text-green-600' : 'text-red-600'}
            bg={summary.total_realized_gain_usd >= 0 ? 'bg-green-50' : 'bg-red-50'}
          />
          <SummaryCard
            label="Transfer Tax Due"
            value={fmtVnd(summary.total_transfer_tax_vnd)}
            icon={ArrowUpDown}
            color="text-orange-600"
            bg="bg-orange-50"
          />
          <SummaryCard
            label="Exempt Amount"
            value={fmtVnd(summary.total_exempt_vnd)}
            icon={ShieldCheck}
            color="text-blue-600"
            bg="bg-blue-50"
          />
          <SummaryCard
            label="Closed / Open Lots"
            value={`${summary.closed_lot_count} / ${summary.open_lot_count}`}
            icon={Calculator}
            color="text-purple-600"
            bg="bg-purple-50"
          />
        </div>
      )}

      {/* Tabs */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="border-b border-gray-200 flex">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
              {tab.count > 0 && (
                <span className="ml-2 bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full text-xs">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        <div className="p-4">
          {activeTab === 'gains' && <GainsTable lots={closedLots} />}
          {activeTab === 'lots' && <OpenLotsTable lots={openLots} />}
          {activeTab === 'transfers' && <TransfersTable transfers={transfers} />}
        </div>
      </div>
    </div>
  )
}

function SummaryCard({ label, value, icon: Icon, color, bg }: {
  label: string; value: string; icon: React.ComponentType<{ className?: string }>; color: string; bg: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-500">{label}</span>
        <div className={`${bg} p-2 rounded-lg`}>
          <Icon className={`w-4 h-4 ${color}`} />
        </div>
      </div>
      <p className="text-xl font-bold text-gray-900">{value}</p>
    </div>
  )
}

function GainsTable({ lots }: { lots: { symbol: string; quantity: number; cost_basis_usd: number; proceeds_usd: number; gain_usd: number; holding_days: number; buy_date: string; sell_date: string }[] }) {
  if (lots.length === 0) return <EmptyState message="No realized gains yet. Run a tax calculation first." />
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 border-b">
            <th className="pb-2 font-medium">Symbol</th>
            <th className="pb-2 font-medium">Quantity</th>
            <th className="pb-2 font-medium">Cost Basis</th>
            <th className="pb-2 font-medium">Proceeds</th>
            <th className="pb-2 font-medium">Gain/Loss</th>
            <th className="pb-2 font-medium">Days Held</th>
            <th className="pb-2 font-medium">Buy Date</th>
            <th className="pb-2 font-medium">Sell Date</th>
          </tr>
        </thead>
        <tbody>
          {lots.map((lot, i) => (
            <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
              <td className="py-2 font-medium">{lot.symbol}</td>
              <td className="py-2">{lot.quantity}</td>
              <td className="py-2">${lot.cost_basis_usd.toLocaleString()}</td>
              <td className="py-2">${lot.proceeds_usd.toLocaleString()}</td>
              <td className={`py-2 font-medium ${lot.gain_usd >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                ${lot.gain_usd.toLocaleString()}
              </td>
              <td className="py-2">{lot.holding_days}d</td>
              <td className="py-2 text-gray-500">{new Date(lot.buy_date).toLocaleDateString()}</td>
              <td className="py-2 text-gray-500">{new Date(lot.sell_date).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function OpenLotsTable({ lots }: { lots: { symbol: string; remaining_quantity: number; cost_basis_per_unit_usd: number; buy_date: string }[] }) {
  if (lots.length === 0) return <EmptyState message="No open lots. All positions are closed or no calculation has been run." />
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 border-b">
            <th className="pb-2 font-medium">Symbol</th>
            <th className="pb-2 font-medium">Remaining Qty</th>
            <th className="pb-2 font-medium">Cost Basis / Unit</th>
            <th className="pb-2 font-medium">Total Cost</th>
            <th className="pb-2 font-medium">Buy Date</th>
          </tr>
        </thead>
        <tbody>
          {lots.map((lot, i) => (
            <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
              <td className="py-2 font-medium">{lot.symbol}</td>
              <td className="py-2">{lot.remaining_quantity}</td>
              <td className="py-2">${lot.cost_basis_per_unit_usd.toLocaleString()}</td>
              <td className="py-2">${(lot.remaining_quantity * lot.cost_basis_per_unit_usd).toLocaleString()}</td>
              <td className="py-2 text-gray-500">{new Date(lot.buy_date).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TransfersTable({ transfers }: { transfers: { timestamp: string; symbol: string; quantity: number; value_vnd: number; tax_amount_vnd: number; exemption_reason: string | null }[] }) {
  if (transfers.length === 0) return <EmptyState message="No taxable transfers. Run a tax calculation to see transfer tax details." />
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 border-b">
            <th className="pb-2 font-medium">Date</th>
            <th className="pb-2 font-medium">Symbol</th>
            <th className="pb-2 font-medium">Quantity</th>
            <th className="pb-2 font-medium">Value (VND)</th>
            <th className="pb-2 font-medium">Tax (VND)</th>
            <th className="pb-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {transfers.map((t, i) => (
            <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
              <td className="py-2 text-gray-500">{new Date(t.timestamp).toLocaleDateString()}</td>
              <td className="py-2 font-medium">{t.symbol}</td>
              <td className="py-2">{t.quantity}</td>
              <td className="py-2">{t.value_vnd.toLocaleString()} VND</td>
              <td className="py-2">{t.tax_amount_vnd.toLocaleString()} VND</td>
              <td className="py-2">
                {t.exemption_reason ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                    <ShieldCheck className="w-3 h-3" />
                    Exempt
                  </span>
                ) : (
                  <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-700">
                    Taxable
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="text-center py-8 text-gray-400 text-sm">{message}</div>
  )
}
