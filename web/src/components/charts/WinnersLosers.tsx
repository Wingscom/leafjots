import type { WinnersLosers as WinnersLosersData } from '../../api/analytics'

interface Props {
  data: WinnersLosersData
  title?: string
}

function formatUSD(value: number): string {
  return `$${Math.abs(value).toLocaleString('en-US', { maximumFractionDigits: 2 })}`
}

export function WinnersLosers({ data, title = 'Winners & Losers' }: Props) {
  const hasData =
    (data?.winners && data.winners.length > 0) ||
    (data?.losers && data.losers.length > 0)

  if (!hasData) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
        <div className="flex items-center justify-center h-48 text-gray-400 text-sm">No data available</div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
      <div className="grid grid-cols-2 gap-4 mt-2">
        {/* Winners column */}
        <div>
          <div className="text-xs font-semibold text-green-600 uppercase tracking-wide mb-2">
            Winners
          </div>
          {data.winners.length === 0 ? (
            <p className="text-xs text-gray-400">No winners</p>
          ) : (
            <ul className="space-y-2">
              {data.winners.map((item) => (
                <li key={item.symbol} className="flex items-center justify-between text-sm">
                  <span className="font-medium text-gray-700">{item.symbol}</span>
                  <span className="text-green-600 font-semibold">+{formatUSD(item.net_gain_usd)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Losers column */}
        <div>
          <div className="text-xs font-semibold text-red-600 uppercase tracking-wide mb-2">
            Losers
          </div>
          {data.losers.length === 0 ? (
            <p className="text-xs text-gray-400">No losers</p>
          ) : (
            <ul className="space-y-2">
              {data.losers.map((item) => (
                <li key={item.symbol} className="flex items-center justify-between text-sm">
                  <span className="font-medium text-gray-700">{item.symbol}</span>
                  <span className="text-red-600 font-semibold">-{formatUSD(item.net_gain_usd)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
