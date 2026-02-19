import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { generateReport, listReports, type ReportGenerateRequest } from '../api/reports'
import { useEntity } from '../context/EntityContext'

const REPORTS_KEY = ['reports'] as const

export function useGenerateReport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: ReportGenerateRequest) => generateReport(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: REPORTS_KEY })
    },
  })
}

export function useReports() {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...REPORTS_KEY, entityId],
    queryFn: () => listReports(entityId ?? undefined),
  })
}
