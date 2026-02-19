import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { listImports, uploadCsv, getImportDetail, parseImport, getImportSummary, getImportRows } from '../api/imports'
import { useEntity } from '../context/EntityContext'

const IMPORTS_KEY = ['imports'] as const

export function useImports() {
  const { entityId } = useEntity()
  return useQuery({
    queryKey: [...IMPORTS_KEY, entityId],
    queryFn: () => listImports(entityId ?? undefined),
  })
}

export function useUploadCsv() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ file, entityId, exchange }: { file: File; entityId: string; exchange?: string }) =>
      uploadCsv(file, entityId, exchange),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: IMPORTS_KEY })
    },
  })
}

export function useImportDetail(importId: string | null) {
  return useQuery({
    queryKey: [...IMPORTS_KEY, 'detail', importId],
    queryFn: () => getImportDetail(importId!),
    enabled: !!importId,
  })
}

export function useParseImport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (importId: string) => parseImport(importId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: IMPORTS_KEY })
    },
  })
}

export function useImportSummary(importId: string | null) {
  return useQuery({
    queryKey: [...IMPORTS_KEY, 'summary', importId],
    queryFn: () => getImportSummary(importId!),
    enabled: !!importId,
  })
}

export function useImportRows(importId: string | null, status?: string) {
  return useQuery({
    queryKey: [...IMPORTS_KEY, 'rows', importId, status],
    queryFn: () => getImportRows(importId!, status),
    enabled: !!importId,
  })
}
