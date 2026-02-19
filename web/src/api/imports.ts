import { apiFetch, withEntityId } from './client'

export interface CsvImport {
  id: string
  entity_id: string
  exchange: string
  filename: string
  row_count: number
  parsed_count: number
  error_count: number
  status: string
  created_at: string
}

export interface CsvImportList {
  imports: CsvImport[]
  total: number
}

export interface UploadResponse {
  import_id: string
  filename: string
  row_count: number
  status: string
}

export async function uploadCsv(
  file: File,
  entityId: string,
  exchange: string = 'binance',
): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('entity_id', entityId)
  formData.append('exchange', exchange)
  const res = await fetch('/api/imports/upload', {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`Upload failed: ${res.status} ${body}`)
  }
  return res.json()
}

export async function listImports(entityId?: string): Promise<CsvImportList> {
  return apiFetch(withEntityId('/imports', entityId))
}

export async function getImportDetail(importId: string): Promise<CsvImport> {
  return apiFetch(`/imports/${importId}`)
}

export interface ParseResult {
  import_id: string
  total: number
  parsed: number
  errors: number
  skipped: number
}

export async function parseImport(importId: string): Promise<ParseResult> {
  return apiFetch(`/imports/${importId}/parse`, { method: 'POST' })
}

export interface ImportSummary {
  import_id: string
  total: number
  operation_counts: Record<string, number>
  status_counts: Record<string, number>
}

export interface CsvImportRow {
  id: string
  row_number: number
  utc_time: string
  account: string
  operation: string
  coin: string
  change: string
  remark: string | null
  status: string
  error_message: string | null
}

export async function getImportSummary(importId: string): Promise<ImportSummary> {
  return apiFetch(`/imports/${importId}/summary`)
}

export async function getImportRows(importId: string, status?: string): Promise<CsvImportRow[]> {
  const path = status ? `/imports/${importId}/rows?status=${status}` : `/imports/${importId}/rows`
  return apiFetch(path)
}
