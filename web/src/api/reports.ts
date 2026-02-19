import { apiFetch, withEntityId } from './client'

export interface ReportGenerateRequest {
  entity_id?: string
  start_date: string
  end_date: string
}

export interface ReportResponse {
  id: string
  entity_id: string
  period_start: string
  period_end: string
  status: string
  filename: string | null
  generated_at: string | null
  error_message: string | null
}

export function generateReport(body: ReportGenerateRequest) {
  return apiFetch<ReportResponse>('/reports/generate', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function listReports(entityId?: string) {
  return apiFetch<ReportResponse[]>(withEntityId('/reports', entityId))
}

export function getReportStatus(id: string) {
  return apiFetch<ReportResponse>(`/reports/${id}/status`)
}

export function downloadReportUrl(id: string) {
  return `/api/reports/${id}/download`
}
