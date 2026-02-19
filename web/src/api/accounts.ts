import { apiFetch, withEntityId } from './client'

export interface Account {
  id: string
  label: string
  wallet_id: string
  account_type: string
  subtype: string
  symbol: string
  token_address: string | null
  protocol: string | null
  balance: number
}

export interface AccountList {
  accounts: Account[]
}

export interface AccountHistorySplit {
  id: string
  journal_entry_id: string
  quantity: number
  value_usd: number | null
  timestamp: string
  entry_type: string
  description: string
}

export interface AccountHistory {
  account: Account
  splits: AccountHistorySplit[]
  total: number
  limit: number
  offset: number
}

export async function listAccounts(entityId?: string): Promise<AccountList> {
  return apiFetch<AccountList>(withEntityId('/accounts', entityId))
}

export async function getAccountHistory(
  accountId: string,
  limit = 50,
  offset = 0,
): Promise<AccountHistory> {
  return apiFetch<AccountHistory>(`/accounts/${accountId}/history?limit=${limit}&offset=${offset}`)
}
