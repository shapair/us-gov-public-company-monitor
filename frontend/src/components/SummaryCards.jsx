function formatNumber(n) {
  if (n === undefined || n === null) return '—'
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(n)
}

function formatCurrency(n) {
  if (n === undefined || n === null) return '—'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

export default function SummaryCards({ summary, monthLabel }) {
  if (!summary) return null

  const cards = [
    { label: 'Total Tracked Events', value: formatNumber(summary.total_events) },
    { label: 'Last 30 Days', value: formatNumber(summary.recent_30d) },
    { label: 'Total Amount', value: formatCurrency(summary.total_amount) },
  ]

  return (
    <div>
      {monthLabel && (
        <div className="mb-3 text-apple-caption text-apple-ink-muted-48">
          Showing data for <span className="font-medium text-apple-ink">{monthLabel}</span>
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {cards.map((card) => (
          <div
            key={card.label}
            className="apple-card-compact flex flex-col justify-between"
          >
            <div className="apple-stat-label mb-1">{card.label}</div>
            <div className="apple-stat-value">{card.value}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
