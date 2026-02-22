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
  /** current_balance from backend, mapped as balance for backwards compat */
  current_balance?: number
  balance_usd: number
  balance_vnd: number
}

export interface AccountList {
  accounts: Account[]
}

export interface AccountHistorySplit {
  id: string
  journal_entry_id: string
  quantity: number
  value_usd: number | null
  value_vnd: number | null
  created_at: string
}

export interface AccountHistory {
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
