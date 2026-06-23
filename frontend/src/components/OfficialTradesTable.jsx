import Pagination from './Pagination'

function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  return isNaN(d) ? value : d.toLocaleDateString('en-US')
}

function formatAmountRange(min, max) {
  if (min == null && max == null) return '—'
  const fmt = (n) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
  if (min != null && max != null) return `${fmt(min)} – ${fmt(max)}`
  if (min != null) return `Over ${fmt(min)}`
  return `Under ${fmt(max)}`
}

function formatAmount(n) {
  if (n == null) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(n)
}

function className(...classes) {
  return classes.filter(Boolean).join(' ')
}

export default function OfficialTradesTable({ trades, offset, limit, total, onPageChange }) {
  return (
    <div className="apple-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-apple-hairline">
          <thead className="bg-apple-pearl">
            <tr>
              <th className="apple-table-header whitespace-nowrap">Date</th>
              <th className="apple-table-header whitespace-nowrap">Ticker</th>
              <th className="apple-table-header whitespace-nowrap">Asset / Company</th>
              <th className="apple-table-header whitespace-nowrap">Official</th>
              <th className="apple-table-header whitespace-nowrap">Chamber</th>
              <th className="apple-table-header whitespace-nowrap">Type</th>
              <th className="apple-table-header whitespace-nowrap">Amount Range</th>
              <th className="apple-table-header whitespace-nowrap">Est. Amount</th>
              <th className="apple-table-header whitespace-nowrap">Filing</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-apple-hairline">
            {trades.length === 0 && (
              <tr>
                <td colSpan={9} className="px-4 py-10 text-center text-apple-ink-muted-48 text-apple-body">
                  No official trades found.
                </td>
              </tr>
            )}
            {trades.map((t) => (
              <tr key={t.id} className="hover:bg-apple-parchment/60 transition-colors">
                <td className="apple-table-cell text-apple-ink-muted-48 whitespace-nowrap">
                  {formatDate(t.transaction_date || t.occurred_at)}
                </td>
                <td className="apple-table-cell font-medium whitespace-nowrap">{t.ticker || '—'}</td>
                <td className={className('apple-table-cell max-w-xs truncate', 'whitespace-nowrap')} title={t.company_name}>
                  {t.company_name || '—'}
                </td>
                <td className="apple-table-cell whitespace-nowrap">{t.official_name || '—'}</td>
                <td className="apple-table-cell whitespace-nowrap">
                  {t.chamber ? t.chamber.charAt(0).toUpperCase() + t.chamber.slice(1) : '—'}
                </td>
                <td className="apple-table-cell whitespace-nowrap">
                  {t.transaction_type
                    ? t.transaction_type.charAt(0).toUpperCase() + t.transaction_type.slice(1)
                    : '—'}
                </td>
                <td className="apple-table-cell whitespace-nowrap">{formatAmountRange(t.amount_min, t.amount_max)}</td>
                <td className="apple-table-cell whitespace-nowrap">{formatAmount(t.amount)}</td>
                <td className="apple-table-cell whitespace-nowrap">
                  {t.filing_url ? (
                    <a
                      href={t.filing_url}
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
