import { useState } from "react";
import { ChevronLeft, ChevronRight, ExternalLink, X } from "lucide-react";
import { clsx } from "clsx";
import { useTransactions, useTransaction } from "../hooks/useTransactions";
import { useWallets } from "../hooks/useWallets";
import {
  FilterBar,
  DateRangePicker,
  WalletSelector,
  ChainSelector,
} from "../components/filters";
import type { TransactionFilters } from "../api/transactions";

const STATUS_STYLES: Record<string, string> = {
  LOADED: "bg-gray-100 text-gray-600",
  PARSED: "bg-green-100 text-green-700",
  ERROR: "bg-red-100 text-red-700",
  IGNORED: "bg-yellow-100 text-yellow-700",
};

const STATUSES = ["", "LOADED", "PARSED", "ERROR", "IGNORED"];
const PAGE_SIZE = 25;

const EXPLORER_URLS: Record<string, string> = {
  ethereum: "https://etherscan.io/tx/",
  arbitrum: "https://arbiscan.io/tx/",
  optimism: "https://optimistic.etherscan.io/tx/",
  polygon: "https://polygonscan.com/tx/",
  base: "https://basescan.org/tx/",
  bsc: "https://bscscan.com/tx/",
  avalanche: "https://snowtrace.io/tx/",
};

function shortenHash(hash: string): string {
  return `${hash.slice(0, 10)}...${hash.slice(-8)}`;
}

function shortenAddr(addr: string | null): string {
  if (!addr) return "\u2014";
  return `${addr.slice(0, 8)}...${addr.slice(-6)}`;
}

function formatTimestamp(ts: number | null): string {
  if (!ts) return "\u2014";
  return new Date(ts * 1000).toLocaleString();
}

function formatWei(wei: number | null): string {
  if (wei === null || wei === undefined) return "\u2014";
  const eth = wei / 1e18;
  if (eth === 0) return "0";
  if (eth < 0.0001) return "<0.0001";
  return eth.toFixed(4);
}

export default function Transactions() {
  const [filters, setFilters] = useState<TransactionFilters>({
    limit: PAGE_SIZE,
    offset: 0,
  });
  const [dateFrom, setDateFrom] = useState<string | null>(null);
  const [dateTo, setDateTo] = useState<string | null>(null);
  const [walletId, setWalletId] = useState<string | null>(null);
  const [chain, setChain] = useState<string | null>(null);
  const [selectedHash, setSelectedHash] = useState<string | null>(null);

  const { data: walletData } = useWallets();
  const wallets = (walletData?.wallets ?? []).map((w) => ({
    id: w.id,
    label: w.label ?? w.address ?? w.id,
  }));

  const activeFilters: TransactionFilters = {
    ...filters,
    date_from: dateFrom ?? undefined,
    date_to: dateTo ?? undefined,
    wallet_id: walletId ?? undefined,
    chain: chain ?? undefined,
  };

  const { data, isLoading, error } = useTransactions(activeFilters);
  const { data: detail } = useTransaction(selectedHash);

  const page = Math.floor((filters.offset ?? 0) / PAGE_SIZE);
  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  function handleReset() {
    setDateFrom(null);
    setDateTo(null);
    setWalletId(null);
    setChain(null);
    setFilters({ limit: PAGE_SIZE, offset: 0 });
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Transactions</h2>

      {/* Filters */}
      <div className="mb-6">
        <FilterBar onReset={handleReset}>
          <DateRangePicker
            dateFrom={dateFrom}
            dateTo={dateTo}
            onDateFromChange={(v) => {
              setDateFrom(v);
              setFilters((f) => ({ ...f, offset: 0 }));
            }}
            onDateToChange={(v) => {
              setDateTo(v);
              setFilters((f) => ({ ...f, offset: 0 }));
            }}
          />
          <WalletSelector
            value={walletId}
            onChange={(v) => {
              setWalletId(v);
              setFilters((f) => ({ ...f, offset: 0 }));
            }}
            wallets={wallets}
          />
          <ChainSelector
            value={chain}
            onChange={(v) => {
              setChain(v);
              setFilters((f) => ({ ...f, offset: 0 }));
            }}
          />
          <div>
            <label className="block text-xs text-gray-500 mb-1">Status</label>
            <select
              value={filters.status ?? ""}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  status: e.target.value || undefined,
                  offset: 0,
                })
              }
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s || "All statuses"}
                </option>
              ))}
            </select>
          </div>
          {data && (
            <span className="text-sm text-gray-500 ml-auto self-center">
              {data.total.toLocaleString()} transaction
              {data.total !== 1 ? "s" : ""}
            </span>
          )}
        </FilterBar>
      </div>

      {/* TX Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">
            Loading transactions...
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-500">
            Failed to load transactions
          </div>
        ) : !data?.transactions.length ? (
          <div className="p-8 text-center text-gray-400">
            No transactions yet. Sync a wallet to load transactions.
          </div>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    TX Hash
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Chain
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Block
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Time
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    From
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    To
                  </th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">
                    Value (ETH)
                  </th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">
                    Status
                  </th>
                  <th className="px-4 py-3 text-center font-medium text-gray-600">
                    Link
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.transactions.map((tx) => (
                  <tr
                    key={tx.id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => setSelectedHash(tx.tx_hash)}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-blue-600">
                      {shortenHash(tx.tx_hash)}
                    </td>
                    <td className="px-4 py-3 capitalize">{tx.chain}</td>
                    <td className="px-4 py-3 text-gray-600">
                      {tx.block_number?.toLocaleString() ?? "\u2014"}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                      {formatTimestamp(tx.timestamp)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-600">
                      {shortenAddr(tx.from_addr)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-600">
                      {shortenAddr(tx.to_addr)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs">
                      {formatWei(tx.value_wei)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={clsx(
                          "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
                          STATUS_STYLES[tx.status] ??
                            "bg-gray-100 text-gray-600",
                        )}
                      >
                        {tx.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {EXPLORER_URLS[tx.chain] && (
                        <a
                          href={`${EXPLORER_URLS[tx.chain]}${tx.tx_hash}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="text-gray-400 hover:text-blue-600 transition-colors"
                        >
                          <ExternalLink className="w-4 h-4 inline" />
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
                <span className="text-sm text-gray-500">
                  Page {page + 1} of {totalPages}
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() =>
                      setFilters({
                        ...filters,
                        offset: Math.max(0, (filters.offset ?? 0) - PAGE_SIZE),
                      })
                    }
                    disabled={page === 0}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-100 disabled:opacity-40 transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" /> Prev
                  </button>
                  <button
                    onClick={() =>
                      setFilters({
                        ...filters,
                        offset: (filters.offset ?? 0) + PAGE_SIZE,
                      })
                    }
                    disabled={page >= totalPages - 1}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-100 disabled:opacity-40 transition-colors"
                  >
                    Next <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* TX Detail Modal */}
      {selectedHash && detail && (
        <div
          className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedHash(null)}
        >
          <div
            className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">
                Transaction Detail
              </h3>
              <button
                onClick={() => setSelectedHash(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="px-6 py-4 space-y-3 text-sm">
              <Row label="TX Hash" value={detail.tx_hash} mono />
              <Row label="Chain" value={detail.chain} />
              <Row
                label="Block"
                value={detail.block_number?.toLocaleString() ?? "\u2014"}
              />
              <Row
                label="Timestamp"
                value={formatTimestamp(detail.timestamp)}
              />
              <Row label="From" value={detail.from_addr ?? "\u2014"} mono />
              <Row label="To" value={detail.to_addr ?? "\u2014"} mono />
              <Row
                label="Value (wei)"
                value={detail.value_wei?.toLocaleString() ?? "\u2014"}
              />
              <Row label="Value (ETH)" value={formatWei(detail.value_wei)} />
              <Row
                label="Gas Used"
                value={detail.gas_used?.toLocaleString() ?? "\u2014"}
              />
              <Row label="Status" value={detail.status} />
              <Row label="Entry Type" value={detail.entry_type ?? "\u2014"} />
              {EXPLORER_URLS[detail.chain] && (
                <div className="pt-2">
                  <a
                    href={`${EXPLORER_URLS[detail.chain]}${detail.tx_hash}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline text-sm flex items-center gap-1"
                  >
                    View on Explorer <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
              )}
              {/* {detail.tx_data && (
                <div className="pt-2">
                  <span className="text-gray-500 text-xs font-medium block mb-1">
                    Raw Data
                  </span>
                  <pre className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-xs font-mono overflow-x-auto max-h-48">
                    {typeof detail.tx_data === "string"
                      ? (() => {
                          try {
                            return JSON.stringify(
                              JSON.parse(detail.tx_data),
                              null,
                              2,
                            );
                          } catch {
                            return detail.tx_data;
                          }
                        })()
                      : JSON.stringify(detail.tx_data, null, 2)}
                  </pre>
                </div>
              )} */}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Row({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex gap-4">
      <span className="w-28 shrink-0 text-gray-500 font-medium">{label}</span>
      <span
        className={clsx("text-gray-900 break-all", mono && "font-mono text-xs")}
      >
        {value}
      </span>
    </div>
  );
}
