import { useState } from 'react'
import { FileSpreadsheet, Download, Clock, CheckCircle, XCircle } from 'lucide-react'
import { useGenerateReport, useReports } from '../hooks/useReports'
import { downloadReportUrl, type ReportResponse } from '../api/reports'

export default function Reports() {
  const [startDate, setStartDate] = useState('2025-01-01')
  const [endDate, setEndDate] = useState('2025-12-31')

  const generateMutation = useGenerateReport()
  const { data: reports } = useReports()

  const handleGenerate = () => {
    generateMutation.mutate({ start_date: startDate, end_date: endDate })
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Reports</h2>

      {/* Generate controls */}
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
          onClick={handleGenerate}
          disabled={generateMutation.isPending}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
        >
          <FileSpreadsheet className="w-4 h-4" />
          {generateMutation.isPending ? 'Generating...' : 'Generate Report'}
        </button>
        {generateMutation.isError && (
          <span className="text-red-500 text-sm">{String(generateMutation.error)}</span>
        )}
      </div>

      {/* Latest result */}
      {generateMutation.data && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <StatusBadge status={generateMutation.data.status} />
              <span className="text-sm font-medium text-gray-700">
                {generateMutation.data.filename}
              </span>
            </div>
            {generateMutation.data.status === 'completed' && (
              <a
                href={downloadReportUrl(generateMutation.data.id)}
                className="bg-green-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-green-700 flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                Download
              </a>
            )}
          </div>
          {generateMutation.data.error_message && (
            <p className="mt-2 text-sm text-red-500">{generateMutation.data.error_message}</p>
          )}
        </div>
      )}

      {/* Report history */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="border-b border-gray-200 px-4 py-3">
          <h3 className="font-semibold text-gray-900">Report History</h3>
        </div>
        <div className="p-4">
          {!reports || reports.length === 0 ? (
            <div className="text-center py-8 text-gray-400 text-sm">
              No reports generated yet. Use the form above to generate your first report.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="pb-2 font-medium">Period</th>
                    <th className="pb-2 font-medium">Filename</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Generated</th>
                    <th className="pb-2 font-medium">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.map((report) => (
                    <ReportRow key={report.id} report={report} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ReportRow({ report }: { report: ReportResponse }) {
  const periodStart = new Date(report.period_start).toLocaleDateString()
  const periodEnd = new Date(report.period_end).toLocaleDateString()
  const generatedAt = report.generated_at
    ? new Date(report.generated_at).toLocaleString()
    : '-'

  return (
    <tr className="border-b border-gray-50 hover:bg-gray-50">
      <td className="py-2">{periodStart} - {periodEnd}</td>
      <td className="py-2 text-gray-500">{report.filename || '-'}</td>
      <td className="py-2"><StatusBadge status={report.status} /></td>
      <td className="py-2 text-gray-500">{generatedAt}</td>
      <td className="py-2">
        {report.status === 'completed' && (
          <a
            href={downloadReportUrl(report.id)}
            className="text-blue-600 hover:text-blue-800 flex items-center gap-1 text-sm"
          >
            <Download className="w-3 h-3" />
            Download
          </a>
        )}
      </td>
    </tr>
  )
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'completed') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
        <CheckCircle className="w-3 h-3" />
        Completed
      </span>
    )
  }
  if (status === 'failed') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
        <XCircle className="w-3 h-3" />
        Failed
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">
      <Clock className="w-3 h-3" />
      Generating
    </span>
  )
}
