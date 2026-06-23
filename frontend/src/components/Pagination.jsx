export default function Pagination({ offset, limit, total, onPageChange }) {
  if (!total || total <= limit) return null

  const currentPage = Math.floor(offset / limit) + 1
  const totalPages = Math.ceil(total / limit)

  const getPageNumbers = () => {
    const pages = []
    const maxVisible = 7
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2))
    let end = Math.min(totalPages, start + maxVisible - 1)
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1)
    }
    for (let i = start; i <= end; i++) {
      pages.push(i)
    }
    return pages
  }

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-apple-canvas">
      <div className="text-apple-caption text-apple-ink-muted-48">
        Showing {offset + 1} to {Math.min(offset + limit, total)} of {total} results
      </div>
      <div className="flex items-center gap-1.5">
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="px-3 py-1.5 rounded-apple-pill border border-apple-hairline text-apple-caption text-apple-ink hover:bg-apple-pearl disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Previous
        </button>
        {getPageNumbers().map((page) => (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            className={`min-w-[32px] px-2 py-1.5 rounded-apple-pill text-apple-caption transition-colors ${
              page === currentPage
                ? 'bg-apple-primary text-white'
                : 'border border-apple-hairline text-apple-ink hover:bg-apple-pearl'
            }`}
          >
            {page}
          </button>
        ))}
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="px-3 py-1.5 rounded-apple-pill border border-apple-hairline text-apple-caption text-apple-ink hover:bg-apple-pearl disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Next
        </button>
      </div>
    </div>
  )
}
