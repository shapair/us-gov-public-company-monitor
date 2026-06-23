import { useEffect, useState } from 'react'
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip as ReTooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts'

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

const TYPE_META = {
  contract: { label: 'Contracts', color: '#0066cc' },
  trade: { label: 'Trades', color: '#34c759' },
  stake: { label: 'Stakes', color: '#7a7a7a' },
  foreign_holding: { label: 'Foreign Holdings', color: '#af52de' },
}

function formatNumber(n) {
  if (n === undefined || n === null) return '—'
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(n)
}

function formatCurrency(n) {
  if (n === undefined || n === null) return '—'
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`
  if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`
  if (n >= 1e6) return `$${(n / 1e6).toFixed(2)}M`
  return `$${formatNumber(n)}`
}

function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return isNaN(d) ? iso : d.toLocaleDateString()
}

function freshnessClass(days) {
  if (days === undefined || days === null) return 'text-apple-ink-muted-48'
  if (days <= 2) return 'text-green-600'
  if (days <= 7) return 'text-amber-600'
  return 'text-red-600'
}

function freshnessBadge(days) {
  if (days === undefined || days === null) return 'bg-gray-100 text-gray-600'
  if (days <= 2) return 'bg-green-100 text-green-700'
  if (days <= 7) return 'bg-amber-100 text-amber-700'
  return 'bg-red-100 text-red-700'
}

function QualityBar({ label, value, color = '#0066cc' }) {
  const pct = Math.min(100, Math.max(0, value || 0))
  return (
    <div className="mb-4">
      <div className="flex justify-between text-apple-caption mb-1.5">
        <span className="text-apple-ink">{label}</span>
        <span className="font-medium text-apple-ink">{pct.toFixed(1)}%</span>
      </div>
      <div className="h-2 w-full rounded-apple-pill bg-apple-pearl overflow-hidden">
        <div
          className="h-full rounded-apple-pill"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  )
}

function MiniPie({ data, colors }) {
  if (!data || data.length === 0) return null
  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="count"
            nameKey="name"
            innerRadius={45}
            outerRadius={70}
            paddingAngle={2}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={colors[i % colors.length]} />
            ))}
          </Pie>
          <ReTooltip
            formatter={(value) => formatNumber(value)}
            contentStyle={{
              borderRadius: 12,
              border: '1px solid #e5e5e5',
              background: '#fff',
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function DataMonitor() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        setLoading(true)
        const res = await fetch(`${API_BASE}/dashboard/monitor`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = await res.json()
        if (!cancelled) setData(json)
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) {
    return (
      <div className="text-center py-20 text-apple-ink-muted-48 text-apple-body">
        Loading monitor data…
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="text-center py-20 text-red-600 text-apple-body">
        Failed to load monitor data: {error || 'unknown error'}
      </div>
    )
  }

  const freshness = (data.freshness || []).sort(
    (a, b) => (b.count || 0) - (a.count || 0)
  )

  const quality = data.quality || {}
  const reviewData = (data.foreign_holdings?.review_status || []).map((r) => ({
    name: r.status,
    count: r.count,
  }))
  const confidenceData = (data.foreign_holdings?.confidence || []).map((c) => ({
    name: c.level,
    count: c.count,
  }))
  const reviewColors = ['#34c759', '#ff9500', '#af52de', '#8e8e93']
  const confidenceColors = ['#34c759', '#ffcc00', '#ff9500', '#ff3b30']

  const missingByType = (quality.by_type || []).map((row) => ({
    type: row.event_type,
    label: TYPE_META[row.event_type]?.label || row.event_type,
    ticker: row.missing_ticker_pct,
    amount: row.missing_amount_pct,
  }))

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <h2 className="apple-section-title">Data Freshness & Quality</h2>
          <p className="text-apple-caption text-apple-ink-muted-48 mt-1">
            Generated at {new Date(data.generated_at).toLocaleString()}
          </p>
        </div>
        <div className="apple-card px-5 py-3 flex items-center gap-4">
          <div>
            <div className="text-apple-caption text-apple-ink-muted-48">Health Score</div>
            <div
              className={`text-[32px] leading-none font-display ${
                quality.health_score >= 90
                  ? 'text-green-600'
                  : quality.health_score >= 70
                  ? 'text-amber-600'
                  : 'text-red-600'
              }`}
            >
              {quality.health_score}
            </div>
          </div>
          <div className="h-10 w-px bg-apple-hairline" />
          <div>
            <div className="text-apple-caption text-apple-ink-muted-48">Total Events</div>
            <div className="text-[24px] leading-none font-display text-apple-ink">
              {formatNumber(quality.total_events)}
            </div>
          </div>
        </div>
      </div>

      {/* Freshness cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {freshness.map((item) => {
          const meta = TYPE_META[item.event_type] || { label: item.event_type, color: '#8e8e93' }
          return (
            <div key={item.event_type} className="apple-card p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: meta.color }}
                  />
                  <span className="text-apple-caption text-apple-ink-muted-48">{meta.label}</span>
                </div>
                <span
                  className={`text-[11px] font-medium px-2 py-0.5 rounded-apple-pill ${freshnessBadge(
                    item.days_since_occurred
                  )}`}
                >
                  {item.days_since_occurred === null
                    ? 'N/A'
                    : `${item.days_since_occurred}d since data`}
                </span>
              </div>
              <div className="text-[28px] leading-tight font-display text-apple-ink">
                {formatNumber(item.count)}
              </div>
              <div className="text-apple-caption text-apple-ink-muted-48 mt-1">
                {formatCurrency(item.total_amount)} total value
              </div>
              <div className="mt-4 space-y-1 text-apple-caption">
                <div className="flex justify-between">
                  <span className="text-apple-ink-muted-48">Latest event</span>
                  <span className={freshnessClass(item.days_since_occurred)}>
                    {formatDate(item.latest_occurred_at)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-apple-ink-muted-48">Last ingested</span>
                  <span className="text-apple-ink">
                    {formatDate(item.latest_created_at)}
                  </span>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Quality overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="apple-card p-6 md:p-8 lg:col-span-2">
          <h3 className="apple-section-title mb-6">Data Quality Overview</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8">
            <QualityBar
              label="Missing Ticker"
              value={quality.missing_ticker_pct}
              color="#ff3b30"
            />
            <QualityBar
              label="Missing Amount"
              value={quality.missing_amount_pct}
              color="#ff9500"
            />
          </div>
          <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-apple-lg bg-apple-pearl/50">
              <div className="text-apple-caption text-apple-ink-muted-48">Missing Ticker</div>
              <div className="text-[22px] font-display text-apple-ink mt-1">
                {formatNumber(quality.missing_ticker)}
              </div>
              <div className="text-apple-caption text-apple-ink-muted-48">
                {quality.missing_ticker_pct?.toFixed(1)}%
              </div>
            </div>
            <div className="p-4 rounded-apple-lg bg-apple-pearl/50">
              <div className="text-apple-caption text-apple-ink-muted-48">Missing Amount</div>
              <div className="text-[22px] font-display text-apple-ink mt-1">
                {formatNumber(quality.missing_amount)}
              </div>
              <div className="text-apple-caption text-apple-ink-muted-48">
                {quality.missing_amount_pct?.toFixed(1)}%
              </div>
            </div>
            <div className="p-4 rounded-apple-lg bg-apple-pearl/50">
              <div className="text-apple-caption text-apple-ink-muted-48">Duplicate IDs</div>
              <div className="text-[22px] font-display text-apple-ink mt-1">
                {formatNumber(quality.duplicate_source_ids)}
              </div>
              <div className="text-apple-caption text-apple-ink-muted-48">source_id groups</div>
            </div>
            <div className="p-4 rounded-apple-lg bg-apple-pearl/50">
              <div className="text-apple-caption text-apple-ink-muted-48">Foreign Pending</div>
              <div className="text-[22px] font-display text-apple-ink mt-1">
                {formatNumber(
                  reviewData.find((r) => r.name === 'pending')?.count || 0
                )}
              </div>
              <div className="text-apple-caption text-apple-ink-muted-48">review queue</div>
            </div>
          </div>
        </div>

        <div className="apple-card p-6 md:p-8">
          <h3 className="apple-section-title mb-2">Foreign Holdings Review</h3>
          <MiniPie data={reviewData} colors={reviewColors} />
          <div className="mt-2 space-y-1.5">
            {reviewData.map((r, i) => (
              <div key={r.name} className="flex items-center justify-between text-apple-caption">
                <div className="flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: reviewColors[i % reviewColors.length] }}
                  />
                  <span className="capitalize text-apple-ink">{r.name}</span>
                </div>
                <span className="text-apple-ink-muted-48">{formatNumber(r.count)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Missing rates by type */}
      {missingByType.length > 0 && (
        <div className="apple-card p-6 md:p-8">
          <h3 className="apple-section-title mb-5">Missing Rates by Category</h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={missingByType} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e5e5" />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 12, fill: '#6e6e73' }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 12, fill: '#6e6e73' }}
                  axisLine={false}
                  tickLine={false}
                  unit="%"
                />
                <ReTooltip
                  formatter={(value) => `${Number(value).toFixed(1)}%`}
                  contentStyle={{
                    borderRadius: 12,
                    border: '1px solid #e5e5e5',
                    background: '#fff',
                  }}
                />
                <Bar dataKey="ticker" name="Missing Ticker" fill="#ff3b30" radius={[4, 4, 0, 0]} />
                <Bar dataKey="amount" name="Missing Amount" fill="#ff9500" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Confidence distribution */}
      {confidenceData.length > 0 && (
        <div className="apple-card p-6 md:p-8">
          <h3 className="apple-section-title mb-5">Foreign Holdings Confidence Distribution</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={confidenceData}
                    dataKey="count"
                    nameKey="name"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={2}
                  >
                    {confidenceData.map((_, i) => (
                      <Cell key={i} fill={confidenceColors[i % confidenceColors.length]} />
                    ))}
                  </Pie>
                  <ReTooltip formatter={(value) => formatNumber(value)} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-3">
              {confidenceData.map((c, i) => (
                <div
                  key={c.name}
                  className="flex items-center justify-between p-3 rounded-apple-lg bg-apple-pearl/50"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: confidenceColors[i % confidenceColors.length] }}
                    />
                    <span className="capitalize text-apple-ink text-apple-body">{c.name}</span>
                  </div>
                  <span className="font-display text-apple-ink">{formatNumber(c.count)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
