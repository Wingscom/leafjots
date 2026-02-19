import { useCallback, useRef, useState } from 'react'
import { Upload, FileText, CheckCircle, Clock, AlertTriangle, XCircle, Play, ChevronRight } from 'lucide-react'
import { useImports, useUploadCsv, useParseImport, useImportSummary, useImportRows } from '../hooks/useImports'
import { useEntity } from '../context/EntityContext'
import type { CsvImport } from '../api/imports'

const EXCHANGES = [
  { value: 'binance', label: 'Binance' },
]

export default function Imports() {
  const { entityId } = useEntity()
  const [exchange, setExchange] = useState('binance')
  const [dragOver, setDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data, isLoading } = useImports()
  const uploadMutation = useUploadCsv()
  const parseMutation = useParseImport()

  const handleUpload = useCallback(
    (file: File) => {
      if (!entityId) return
      uploadMutation.mutate({ file, entityId, exchange }, {
        onSuccess: (data) => {
          // Auto-trigger parse after successful upload
          parseMutation.mutate(data.import_id)
        },
      })
    },
    [entityId, exchange, uploadMutation, parseMutation],
  )

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleUpload(file)
    // Reset so re-selecting the same file works
    e.target.value = ''
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file) handleUpload(file)
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">CSV Import</h2>

      {/* Upload area */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <div className="flex items-end gap-4 mb-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Exchange</label>
            <select
              value={exchange}
              onChange={(e) => setExchange(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
            >
              {EXCHANGES.map((ex) => (
                <option key={ex.value} value={ex.value}>
                  {ex.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
            dragOver
              ? 'border-blue-400 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
          onDragOver={(e) => {
            e.preventDefault()
            setDragOver(true)
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
          <p className="text-sm text-gray-600 mb-1">
            Drag and drop a CSV file here, or click to browse
          </p>
          <p className="text-xs text-gray-400">
            Supports Binance Transaction History export format
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>

        {/* Combined upload + parse progress indicator */}
        {(uploadMutation.isPending || parseMutation.isPending) && (
          <div className="mt-3 flex items-center gap-2 text-sm text-blue-600">
            <Clock className="w-4 h-4 animate-spin" />
            {uploadMutation.isPending ? 'Uploading...' : 'Parsing rows...'}
          </div>
        )}

        {parseMutation.isSuccess && !uploadMutation.isPending && !parseMutation.isPending && (
          <div className="mt-3 flex items-center gap-2 text-sm text-green-600">
            <CheckCircle className="w-4 h-4" />
            Parsed: {parseMutation.data.parsed} / {parseMutation.data.total} rows
            {parseMutation.data.errors > 0 && (
              <span className="text-red-600"> ({parseMutation.data.errors} errors)</span>
            )}
          </div>
        )}

        {!parseMutation.isSuccess && uploadMutation.isSuccess && !uploadMutation.isPending && !parseMutation.isPending && (
          <div className="mt-3 flex items-center gap-2 text-sm text-green-600">
            <CheckCircle className="w-4 h-4" />
            Uploaded {uploadMutation.data.filename} ({uploadMutation.data.row_count} rows)
          </div>
        )}

        {uploadMutation.isError && (
          <div className="mt-3 flex items-center gap-2 text-sm text-red-600">
            <XCircle className="w-4 h-4" />
            {String(uploadMutation.error)}
          </div>
        )}

        {parseMutation.isError && !uploadMutation.isError && (
          <div className="mt-3 flex items-center gap-2 text-sm text-red-600">
            <XCircle className="w-4 h-4" />
            Parse failed: {String(parseMutation.error)}
          </div>
        )}

        {!entityId && (
          <div className="mt-3 flex items-center gap-2 text-sm text-yellow-600">
            <AlertTriangle className="w-4 h-4" />
            Select an entity first to upload CSV files
          </div>
        )}
      </div>

      {/* Import history */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="border-b border-gray-200 px-4 py-3">
          <h3 className="font-semibold text-gray-900">Import History</h3>
        </div>
        <div className="p-4">
          {isLoading ? (
            <div className="text-center py-8 text-gray-400 text-sm">Loading...</div>
          ) : !data || data.imports.length === 0 ? (
            <div className="text-center py-8 text-gray-400 text-sm">
              No imports yet. Upload a CSV file above to get started.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="pb-2 w-6"></th>
                    <th className="pb-2 font-medium">Filename</th>
                    <th className="pb-2 font-medium">Exchange</th>
                    <th className="pb-2 font-medium">Date</th>
                    <th className="pb-2 font-medium">Rows</th>
                    <th className="pb-2 font-medium">Parsed</th>
                    <th className="pb-2 font-medium">Errors</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.imports.map((imp) => (
                    <ImportRow key={imp.id} imp={imp} />
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

function ImportRow({ imp }: { imp: CsvImport }) {
  const [expanded, setExpanded] = useState(false)
  const createdAt = new Date(imp.created_at).toLocaleString()
  const parseMutation = useParseImport()
  const canParse = imp.status === 'uploaded' || imp.status === 'completed'

  return (
    <>
      <tr
        className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <td className="py-2">
          <ChevronRight className={`w-4 h-4 text-gray-400 transition-transform ${expanded ? 'rotate-90' : ''}`} />
        </td>
        <td className="py-2">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-gray-400" />
            {imp.filename}
          </div>
        </td>
        <td className="py-2 text-gray-500 capitalize">{imp.exchange}</td>
        <td className="py-2 text-gray-500">{createdAt}</td>
        <td className="py-2">{imp.row_count}</td>
        <td className="py-2 text-gray-500">{imp.parsed_count}</td>
        <td className="py-2">
          {imp.error_count > 0 ? (
            <span className="text-red-600">{imp.error_count}</span>
          ) : (
            <span className="text-gray-400">0</span>
          )}
        </td>
        <td className="py-2">
          <StatusBadge status={imp.status} />
        </td>
        <td className="py-2">
          <button
            onClick={(e) => {
              e.stopPropagation()
              parseMutation.mutate(imp.id)
            }}
            disabled={!canParse || parseMutation.isPending}
            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
              canParse && !parseMutation.isPending
                ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            <Play className="w-3 h-3" />
            {parseMutation.isPending ? 'Parsing...' : 'Parse'}
          </button>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={9} className="p-4 bg-gray-50 border-b">
            <ImportDetail importId={imp.id} errorCount={imp.error_count} />
          </td>
        </tr>
      )}
    </>
  )
}

function ImportDetail({ importId, errorCount }: { importId: string; errorCount: number }) {
  const { data: summary } = useImportSummary(importId)

  if (!summary) return <div className="text-sm text-gray-400">Loading summary...</div>

  return (
    <div>
      {/* Status breakdown: 4 stat cards */}
      <div className="grid grid-cols-4 gap-3 mb-4">
        <StatCard label="Total" value={summary.total} color="gray" />
        <StatCard label="Parsed" value={summary.status_counts.parsed || 0} color="green" />
        <StatCard label="Errors" value={summary.status_counts.error || 0} color="red" />
        <StatCard label="Skipped" value={summary.status_counts.skipped || 0} color="yellow" />
      </div>

      {/* Operation breakdown */}
      {Object.keys(summary.operation_counts).length > 0 && (
        <>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Operations</h4>
          <div className="flex flex-wrap gap-2 mb-4">
            {Object.entries(summary.operation_counts)
              .sort(([, a], [, b]) => b - a)
              .map(([op, count]) => (
                <span key={op} className="text-xs bg-white border rounded-full px-2.5 py-1 text-gray-600">
                  {op}: <span className="font-medium">{count}</span>
                </span>
              ))}
          </div>
        </>
      )}

      {/* Error rows */}
      {errorCount > 0 && <ErrorRows importId={importId} />}
    </div>
  )
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  const colors: Record<string, string> = {
    gray: 'bg-gray-50 text-gray-700',
    green: 'bg-green-50 text-green-700',
    red: 'bg-red-50 text-red-700',
    yellow: 'bg-yellow-50 text-yellow-700',
  }
  return (
    <div className={`rounded-lg p-3 ${colors[color] || colors.gray}`}>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs opacity-75">{label}</div>
    </div>
  )
}

function ErrorRows({ importId }: { importId: string }) {
  const { data: rows } = useImportRows(importId, 'error')
  if (!rows || rows.length === 0) return null

  return (
    <div>
      <h4 className="text-sm font-medium text-red-700 mb-2">Failed Rows ({rows.length})</h4>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {rows.map((row) => (
          <div key={row.id} className="bg-red-50 border border-red-200 rounded-lg p-3 text-xs">
            <div className="flex justify-between mb-1">
              <span className="font-mono text-gray-500">Row #{row.row_number}</span>
              <span className="text-red-600 font-medium">{row.operation}</span>
            </div>
            <div className="grid grid-cols-4 gap-2 text-gray-600 mb-2">
              <span>{row.utc_time}</span>
              <span>{row.account}</span>
              <span>{row.coin}</span>
              <span>{row.change}</span>
            </div>
            {row.error_message && (
              <div className="text-red-700 bg-red-100 rounded p-2 font-mono break-all">
                {row.error_message}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
          <CheckCircle className="w-3 h-3" />
          Completed
        </span>
      )
    case 'parsing':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">
          <Clock className="w-3 h-3" />
          Parsing
        </span>
      )
    case 'error':
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
          <XCircle className="w-3 h-3" />
          Error
        </span>
      )
    default:
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
          <Upload className="w-3 h-3" />
          Uploaded
        </span>
      )
  }
}
