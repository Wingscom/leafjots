const PROTOCOLS = [
  { value: 'aave_v3', label: 'Aave V3' },
  { value: 'uniswap_v3', label: 'Uniswap V3' },
  { value: 'curve', label: 'Curve' },
  { value: 'pancakeswap', label: 'PancakeSwap' },
  { value: 'morpho_blue', label: 'Morpho Blue' },
  { value: 'lido', label: 'Lido' },
  { value: 'pendle', label: 'Pendle' },
]

interface ProtocolSelectorProps {
  value: string | null
  onChange: (v: string | null) => void
}

export default function ProtocolSelector({ value, onChange }: ProtocolSelectorProps) {
  return (
    <div>
      <label className="block text-xs text-gray-500 mb-1">Protocol</label>
      <select
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <option value="">All Protocols</option>
        {PROTOCOLS.map((p) => (
          <option key={p.value} value={p.value}>
            {p.label}
          </option>
        ))}
      </select>
    </div>
  )
}
