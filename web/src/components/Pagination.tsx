import { clsx } from 'clsx'

interface PaginationProps {
  total: number
  limit: number
  offset: number
  onChange: (offset: number) => void
}

function getPageNumbers(currentPage: number, totalPages: number): (number | '...')[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1)
  }

  const pages: (number | '...')[] = [1]

  if (currentPage > 3) {
    pages.push('...')
  }

  const start = Math.max(2, currentPage - 1)
  const end = Math.min(totalPages - 1, currentPage + 1)

  for (let i = start; i <= end; i++) {
    pages.push(i)
  }

  if (currentPage < totalPages - 2) {
    pages.push('...')
  }

  if (totalPages > 1) {
    pages.push(totalPages)
  }

  return pages
}

export default function Pagination({ total, limit, offset, onChange }: PaginationProps) {
  if (total === 0) return null

  const totalPages = Math.ceil(total / limit)
  const currentPage = Math.floor(offset / limit) + 1
  const showingFrom = offset + 1
  const showingTo = Math.min(offset + limit, total)

  const goToPage = (page: number) => {
    onChange((page - 1) * limit)
  }

  const pages = getPageNumbers(currentPage, totalPages)

  return (
    <div className="flex items-center justify-between px-2 py-3">
      <p className="text-sm text-gray-500">
        Showing {showingFrom}-{showingTo} of {total}
      </p>
      <div className="flex items-center gap-1">
        <button
          onClick={() => goToPage(currentPage - 1)}
          disabled={currentPage <= 1}
          className={clsx(
            'px-3 py-1 rounded text-sm border border-gray-300',
            currentPage <= 1
              ? 'opacity-50 cursor-not-allowed text-gray-400'
              : 'text-gray-700 hover:bg-gray-50'
          )}
        >
          Previous
        </button>
        {pages.map((page, idx) =>
          page === '...' ? (
            <span key={`ellipsis-${idx}`} className="px-2 py-1 text-sm text-gray-400">
              ...
            </span>
          ) : (
            <button
              key={page}
              onClick={() => goToPage(page)}
              className={clsx(
                'px-3 py-1 rounded text-sm',
                page === currentPage
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-700 hover:bg-gray-50 border border-gray-300'
              )}
            >
              {page}
            </button>
          )
        )}
        <button
          onClick={() => goToPage(currentPage + 1)}
          disabled={currentPage >= totalPages}
          className={clsx(
            'px-3 py-1 rounded text-sm border border-gray-300',
            currentPage >= totalPages
              ? 'opacity-50 cursor-not-allowed text-gray-400'
              : 'text-gray-700 hover:bg-gray-50'
          )}
        >
          Next
        </button>
      </div>
    </div>
  )
}
