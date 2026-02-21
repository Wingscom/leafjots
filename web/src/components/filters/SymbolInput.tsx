interface SymbolInputProps {
  value: string
  onChange: (v: string) => void
}

export default function SymbolInput({ value, onChange }: SymbolInputProps) {
  return (
    <div>
      <label className="block text-xs text-gray-500 mb-1">Symbol</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Filter by symbol..."
        className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  )
}
