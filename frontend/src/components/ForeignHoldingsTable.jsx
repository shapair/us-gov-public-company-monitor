import Pagination from './Pagination'

function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  return isNaN(d) ? value : d.toLocaleDateString('en-US')
}

function formatAmount(n) {
  if (n == null) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(n)
}

function formatShares(n) {
  if (n == null) return '—'
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(n)
}

function capitalize(value) {
  if (!value) return '—'
  return value.charAt(0).toUpperCase() + value.slice(1)
}

export default function ForeignHoldingsTable({ holdings, offset, limit, total, onPageChange }) {
  return (
    <div className="apple-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-apple-hairline">
          <thead className="bg-apple-pearl">
            <tr>
              <th className="apple-table-header whitespace-nowrap">Period</th>
              <th className="apple-table-header whitespace-nowrap">Ticker</th>
              <th className="apple-table-header whitespace-nowrap">Company</th>
              <th className="apple-table-header whitespace-nowrap">Filer</th>
              <th className="apple-table-header whitespace-nowrap">Filing</th>
              <th className="apple-table-header whitespace-nowrap">Shares</th>
              <th className="apple-table-header whitespace-nowrap">Value</th>
              <th className="apple-table-header whitespace-nowrap">Confidence</th>
              <th className="apple-table-header whitespace-nowrap">Source</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-apple-hairline">
            {holdings.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-10 text-center text-apple-ink-muted-48 text-apple-body">
                  No foreign government holdings found.
                </td>
              </tr>
            )}
            {holdings.map((h) => (
              <tr key={h.id} className="hover:bg-apple-parchment/60 transition-colors">
                <td className="apple-table-cell text-apple-ink-muted-48 whitespace-nowrap">
                  {formatDate(h.period_date || h.filing_date || h.occurred_at)}
                </td>
                <td className="apple-table-cell font-medium whitespace-nowrap">{h.ticker || '—'}</td>
                <td className="apple-table-cell max-w-xs truncate whitespace-nowrap" title={h.company_name}>
                  {h.company_name || '—'}
                </td>
                <td className="apple-table-cell max-w-xs truncate whitespace-nowrap" title={h.filer_name}>
                  {h.filer_name || '—'}
                </td>
                <td className="apple-table-cell whitespace-nowrap">{h.filing_type || '—'}</td>
                <td className="apple-table-cell whitespace-nowrap">{formatShares(h.shares)}</td>
                <td className="apple-table-cell whitespace-nowrap">{formatAmount(h.value)}</td>
                <td className="apple-table-cell whitespace-nowrap">{capitalize(h.confidence)}</td>
                <td className="apple-table-cell whitespace-nowrap">
                  {h.source_url || h.url ? (
                    <a
                      href={h.source_url || h.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-apple-primary hover:underline"
                    >
                      View
                    </a>
                  ) : (
                    '—'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {total > limit && (
        <div className="px-4 py-3 border-t border-apple-hairline">
          <Pagination offset={offset} limit={limit} total={total} onPageChange={onPageChange} />
        </div>
      )}
    </div>
  )
}
