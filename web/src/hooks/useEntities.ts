import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createEntity,
  deleteEntity,
  listEntities,
  updateEntity,
  type EntityCreateRequest,
  type EntityUpdateRequest,
} from '../api/entities'

export const ENTITIES_KEY = ['entities'] as const

export function useEntities() {
  return useQuery({
    queryKey: ENTITIES_KEY,
    queryFn: listEntities,
  })
}

export function useCreateEntity() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: EntityCreateRequest) => createEntity(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ENTITIES_KEY })
    },
  })
}

export function useUpdateEntity() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: EntityUpdateRequest }) => updateEntity(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ENTITIES_KEY })
    },
  })
}

export function useDeleteEntity() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteEntity(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ENTITIES_KEY })
    },
  })
}
