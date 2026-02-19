import { apiFetch } from './client'

export interface Entity {
  id: string
  name: string
  base_currency: string
  wallet_count: number
  created_at: string
  updated_at: string
}

export interface EntityList {
  entities: Entity[]
  total: number
}

export interface EntityCreateRequest {
  name: string
  base_currency?: string
}

export interface EntityUpdateRequest {
  name?: string
  base_currency?: string
}

export async function listEntities(): Promise<EntityList> {
  return apiFetch<EntityList>('/entities')
}

export async function createEntity(data: EntityCreateRequest): Promise<Entity> {
  return apiFetch<Entity>('/entities', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getEntity(id: string): Promise<Entity> {
  return apiFetch<Entity>(`/entities/${id}`)
}

export async function updateEntity(id: string, data: EntityUpdateRequest): Promise<Entity> {
  return apiFetch<Entity>(`/entities/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function deleteEntity(id: string): Promise<void> {
  return apiFetch<void>(`/entities/${id}`, { method: 'DELETE' })
}
