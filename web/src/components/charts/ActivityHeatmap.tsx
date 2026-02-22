import type { ActivityDay } from '../../api/analytics'

interface Props {
  data: ActivityDay[]
  title?: string
}

function getIntensityClass(value: number, max: number): string {
  if (max === 0 || value === 0) return 'bg-gray-100'
  const ratio = value / max
  if (ratio < 0.2) return 'bg-green-100'
  if (ratio < 0.4) return 'bg-green-200'
  if (ratio < 0.6) return 'bg-green-300'
  if (ratio < 0.8) return 'bg-green-400'
  return 'bg-green-500'
}

function parseDate(dateStr: string): Date {
  return new Date(dateStr + 'T00:00:00Z')
}

export function ActivityHeatmap({ data, title = 'Activity Heatmap' }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
        <div className="flex items-center justify-center h-48 text-gray-400 text-sm">No data available</div>
      </div>
    )
  }

  // Build a lookup map: date -> ActivityDay
  const lookup: Record<string, ActivityDay> = {}
  for (const day of data) {
    lookup[day.date] = day
  }

  const maxVolume = Math.max(...data.map((d) => d.volume_usd), 0)

  // Calculate date range: start from earliest Sunday before the first data point
  const dates = data.map((d) => parseDate(d.date)).sort((a, b) => a.getTime() - b.getTime())
  if (dates.length === 0) return null

  const startDate = new Date(dates[0])
  // Walk back to Sunday
  startDate.setUTCDate(startDate.getUTCDate() - startDate.getUTCDay())

  const endDate = new Date(dates[dates.length - 1])
  // Walk forward to Saturday
  endDate.setUTCDate(endDate.getUTCDate() + (6 - endDate.getUTCDay()))

  // Build a grid of weeks
  const weeks: (ActivityDay | null)[][] = []
  const cursor = new Date(startDate)
  let week: (ActivityDay | null)[] = []

  while (cursor <= endDate) {
    const dateStr = cursor.toISOString().slice(0, 10)
    week.push(lookup[dateStr] ?? null)

    if (cursor.getUTCDay() === 6) {
      weeks.push(week)
      week = []
    }
    cursor.setUTCDate(cursor.getUTCDate() + 1)
  }
  if (week.length > 0) {
    while (week.length < 7) week.push(null)
    weeks.push(week)
  }

  const DAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">{title}</h3>
      <div className="overflow-x-auto">
        <div className="flex gap-0.5">
          {/* Day labels */}
          <div className="flex flex-col gap-0.5 mr-1">
            {DAY_LABELS.map((label) => (
              <div
                key={label}
                className="text-xs text-gray-400 h-3 flex items-center"
                style={{ minWidth: '24px' }}
              >
                {label[0]}
              </div>
            ))}
          </div>

          {/* Weeks grid */}
          {weeks.map((week, wi) => (
            <div key={wi} className="flex flex-col gap-0.5">
              {week.map((day, di) => (
                <div
                  key={di}
                  className={`w-3 h-3 rounded-sm ${day ? getIntensityClass(day.volume_usd, maxVolume) : 'bg-gray-50'}`}
                  title={
                    day
                      ? `${day.date}: ${day.entry_count} entries, $${day.volume_usd.toLocaleString('en-US', { maximumFractionDigits: 0 })}`
                      : undefined
                  }
                />
              ))}
            </div>
          ))}
        </div>

        {/* Legend */}
        <div className="flex items-center gap-1 mt-3">
          <span className="text-xs text-gray-400">Less</span>
          {['bg-gray-100', 'bg-green-100', 'bg-green-200', 'bg-green-300', 'bg-green-400', 'bg-green-500'].map((cls) => (
            <div key={cls} className={`w-3 h-3 rounded-sm ${cls}`} />
          ))}
          <span className="text-xs text-gray-400">More</span>
        </div>
      </div>
    </div>
  )
}
