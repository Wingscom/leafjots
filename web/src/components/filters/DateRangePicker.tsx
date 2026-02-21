interface DateRangePickerProps {
  dateFrom: string | null
  dateTo: string | null
  onDateFromChange: (v: string | null) => void
  onDateToChange: (v: string | null) => void
}

export default function DateRangePicker({
  dateFrom,
  dateTo,
  onDateFromChange,
  onDateToChange,
}: DateRangePickerProps) {
  return (
    <div className="flex items-end gap-2">
      <div>
        <label className="block text-xs text-gray-500 mb-1">From</label>
        <input
          type="date"
          value={dateFrom ?? ''}
          onChange={(e) => onDateFromChange(e.target.value || null)}
          className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <div>
        <label className="block text-xs text-gray-500 mb-1">To</label>
        <input
          type="date"
          value={dateTo ?? ''}
          onChange={(e) => onDateToChange(e.target.value || null)}
          className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
    </div>
  )
}
