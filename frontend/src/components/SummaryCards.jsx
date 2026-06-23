function formatNumber(n) {
  if (n === undefined || n === null) return '—'
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(n)
}

function formatCurrency(n) {
  if (n === undefined || n === null) return '—'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

export default function SummaryCards({ summary }) {
  if (!summary) return null

  const cards = [
    { label: 'Total Tracked Events', value: formatNumber(summary.total_events) },
    { label: 'Last 30 Days', value: formatNumber(summary.recent_30d) },
    { label: 'Total Amount', value: formatCurrency(summary.total_amount) },
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
      {cards.map((card) => (
        <div
          key={card.label}
          className="apple-card p-6 flex flex-col justify-between min-h-[120px]"
        >
          <div className="text-apple-caption text-apple-ink-muted-48 mb-2">{card.label}</div>
          <div className="text-[32px] leading-tight tracking-[-0.2px] font-display text-apple-ink">
            {card.value}
          </div>
        </div>
      ))}
    </div>
  )
}
