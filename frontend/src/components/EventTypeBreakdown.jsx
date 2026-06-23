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
    <div className="apple-card p-6 md:p-8">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-6">
        <div>
          <h2 className="apple-section-title">Event Breakdown</h2>
          <p className="text-apple-caption text-apple-ink-muted-48 mt-1">
            {formatNumber(total)} tracked events across {rows.length} categories
          </p>
        </div>
        <div className="text-apple-caption text-apple-ink-muted-48">
          Last updated from live data feeds
        </div>
      </div>

      <div className="h-3 w-full rounded-apple-pill overflow-hidden flex bg-apple-pearl">
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

      <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
        {rows.map((row) => (
          <div
            key={row.type}
            className="flex items-start gap-3 p-4 rounded-apple-lg bg-apple-pearl/50"
          >
            <span
              className="mt-1.5 w-2.5 h-2.5 rounded-full shrink-0"
              style={{ backgroundColor: row.color }}
            />
            <div>
              <div className="text-apple-caption text-apple-ink-muted-48">{row.label}</div>
              <div className="text-[28px] leading-tight font-display text-apple-ink mt-1">
                {formatNumber(row.count)}
              </div>
              <div className="text-apple-caption text-apple-ink-muted-48 mt-0.5">
                {row.percent < 0.1 ? '<0.1%' : `${row.percent.toFixed(1)}%`} of total
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
