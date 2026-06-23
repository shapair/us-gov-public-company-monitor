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

function capitalize(value) {
  if (!value) return '—'
  return value.charAt(0).toUpperCase() + value.slice(1)
}

export default function FederalStakesTable({ stakes, offset, limit, total, onPageChange }) {
  return (
    <div className="apple-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-apple-hairline">
          <thead className="bg-apple-pearl">
            <tr>
              <th className="apple-table-header whitespace-nowrap">Date</th>
              <th className="apple-table-header whitespace-nowrap">Ticker</th>
              <th className="apple-table-header whitespace-nowrap">Company</th>
              <th className="apple-table-header whitespace-nowrap">Agency</th>
              <th className="apple-table-header whitespace-nowrap">Stake Type</th>
              <th className="apple-table-header whitespace-nowrap">Amount</th>
              <th className="apple-table-header whitespace-nowrap">Confidence</th>
              <th className="apple-table-header whitespace-nowrap">Status</th>
              <th className="apple-table-header whitespace-nowrap">Source</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-apple-hairline">
            {stakes.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-10 text-center text-apple-ink-muted-48 text-apple-body">
                  No federal stake events found.
                </td>
              </tr>
            )}
            {stakes.map((s) => (
              <tr key={s.id} className="hover:bg-apple-parchment/60 transition-colors">
                <td className="apple-table-cell text-apple-ink-muted-48 whitespace-nowrap">
                  {formatDate(s.announcement_date || s.occurred_at)}
                </td>
                <td className="apple-table-cell font-medium whitespace-nowrap">{s.ticker || '—'}</td>
                <td className="apple-table-cell max-w-xs truncate whitespace-nowrap" title={s.company_name}>
                  {s.company_name || '—'}
                </td>
                <td className="apple-table-cell whitespace-nowrap">{capitalize(s.agency)}</td>
                <td className="apple-table-cell whitespace-nowrap">{capitalize(s.stake_type).replace(/_/g, ' ')}</td>
                <td className="apple-table-cell whitespace-nowrap">{formatAmount(s.amount)}</td>
                <td className="apple-table-cell whitespace-nowrap">{capitalize(s.confidence)}</td>
                <td className="apple-table-cell whitespace-nowrap">{capitalize(s.review_status)}</td>
                <td className="apple-table-cell whitespace-nowrap">
                  {s.source_url || s.url ? (
                    <a
                      href={s.source_url || s.url}
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
