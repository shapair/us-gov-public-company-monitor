function formatNumber(n) {
  if (n === undefined || n === null) return '—'
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(n)
}

const TYPE_META = {
  contract: { label: 'Government Contracts', color: '#0066cc' },
  trade: { label: 'Official Stock Trades', color: '#34c759' },
  stake: { label: 'Federal Direct Stakes', color: '#7a7a7a' },
  foreign_holding: { label: 'Foreign Government Holdings', color: '#af52de' },
}

export default function EventTypeBreakdown({ by_type }) {
  if (!by_type || by_type.length === 0) return null

  const total = by_type.reduce((sum, item) => sum + (item.count || 0), 0)
  const rows = by_type
    .map((item) => ({
      type: item.type,
      count: item.count,
      percent: total ? (item.count / total) * 100 : 0,
      ...TYPE_META[item.type],
    }))
    .sort((a, b) => b.count - a.count)

  return (
    <div className="apple-card p-5">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 mb-4">
        <div>
          <h2 className="apple-section-title">Event Breakdown</h2>
          <p className="apple-section-subtitle mt-0.5">
            {formatNumber(total)} events across {rows.length} categories
          </p>
        </div>
      </div>

      <div className="h-2.5 w-full rounded-apple-pill overflow-hidden flex bg-apple-pearl">
        {rows.map((row) => (
          <div
            key={row.type}
            style={{
              width: `${row.percent}%`,
              backgroundColor: row.color,
            }}
            className="h-full first:rounded-l-apple-pill last:rounded-r-apple-pill"
            title={`${row.label}: ${formatNumber(row.count)} (${row.percent.toFixed(1)}%)`}
          />
        ))}
      </div>

      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
        {rows.map((row) => (
          <div
            key={row.type}
            className="flex items-start gap-2.5 p-3 rounded-apple-lg bg-apple-pearl/50"
          >
            <span
              className="mt-1.5 w-2 h-2 rounded-full shrink-0"
              style={{ backgroundColor: row.color }}
            />
            <div className="min-w-0">
              <div className="text-apple-caption text-apple-ink-muted-48 truncate">{row.label}</div>
              <div className="text-[22px] leading-tight font-display text-apple-ink mt-0.5">
                {formatNumber(row.count)}
              </div>
              <div className="text-apple-caption text-apple-ink-muted-48 mt-0.5">
                {row.percent < 0.1 ? '<0.1%' : `${row.percent.toFixed(1)}%`}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
