import { Sparkles } from 'lucide-react'

interface AIInsightProps {
  context?: string  // e.g. "analytics", "tax", "journal"
  data?: unknown    // data to analyze
}

export default function AIInsight({ context: _context, data: _data }: AIInsightProps) {
  return (
    <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-xl p-4 opacity-75">
      <div className="flex items-center gap-3">
        <Sparkles className="w-5 h-5 text-purple-400 shrink-0" />
        <div className="flex-1">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-purple-800">AI Insights</p>
              <p className="text-xs text-purple-600 mt-0.5">
                Coming soon — AI-powered analysis of your portfolio and tax data.
              </p>
            </div>
            <button
              disabled
              className="px-3 py-1.5 text-sm text-purple-400 bg-white border border-purple-200 rounded-lg cursor-not-allowed opacity-60 shrink-0"
            >
              Generate Insight
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
