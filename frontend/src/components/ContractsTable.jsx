import Pagination from './Pagination'

function formatCurrency(n) {
  if (n === undefined || n === null) return '—'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

function formatDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString()
}

function truncate(text, maxLen = 120) {
  if (!text) return '—'
  if (text.length <= maxLen) return text
  return text.slice(0, maxLen) + '…'
}

export default function ContractsTable({ contracts, offset, limit, total, onPageChange }) {
  if (contracts.length === 0) {
    return (
      <div className="apple-card p-10 text-center text-apple-ink-muted-48 text-apple-body">
        No contract data available yet.
      </div>
    )
  }

  return (
    <div className="apple-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left">
          <thead className="bg-apple-pearl">
            <tr>
              <th className="apple-table-header whitespace-nowrap">Date</th>
              <th className="apple-table-header whitespace-nowrap">Ticker</th>
              <th className="apple-table-header whitespace-nowrap">Company</th>
              <th className="apple-table-header whitespace-nowrap">Agency</th>
              <th className="apple-table-header whitespace-nowrap">Sub Agency</th>
              <th className="apple-table-header whitespace-nowrap">Award Type</th>
              <th className="apple-table-header whitespace-nowrap">NAICS</th>
              <th className="apple-table-header whitespace-nowrap">PSC</th>
              <th className="apple-table-header whitespace-nowrap">Place</th>
              <th className="apple-table-header whitespace-nowrap">UEI</th>
              <th className="apple-table-header whitespace-nowrap">DUNS</th>
              <th className="apple-table-header text-right whitespace-nowrap">Amount</th>
              <th className="apple-table-header whitespace-nowrap">Description</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-apple-hairline">
            {contracts.map((c) => (
              <tr key={c.id} className="hover:bg-apple-parchment/60 transition-colors">
                <td className="apple-table-cell whitespace-nowrap">{formatDate(c.occurred_at)}</td>
                <td className="apple-table-cell whitespace-nowrap font-medium">{c.ticker || '—'}</td>
                <td className="apple-table-cell whitespace-nowrap">{c.company_name || '—'}</td>
                <td className="apple-table-cell whitespace-nowrap">{c.agency || '—'}</td>
                <td className="apple-table-cell whitespace-nowrap">{c.subagency || '—'}</td>
                <td className="apple-table-cell whitespace-nowrap">{c.award_type || '—'}</td>
                <td className="apple-table-cell whitespace-nowrap">{c.naics || '—'}</td>
                <td className="apple-table-cell whitespace-nowrap">{c.psc || '—'}</td>
                <td className="apple-table-cell whitespace-nowrap">{c.place_of_performance || '—'}</td>
                <td className="apple-table-cell whitespace-nowrap">{c.uei || '—'}</td>
                <td className="apple-table-cell whitespace-nowrap">{c.duns || '—'}</td>
                <td className="apple-table-cell text-right whitespace-nowrap">{formatCurrency(c.amount)}</td>
                <td className="apple-table-cell max-w-md truncate" title={c.description || ''}>
                  {truncate(c.description)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pagination offset={offset} limit={limit} total={total} onPageChange={onPageChange} />
    </div>
  )
}
