import { useEffect, useMemo, useState } from 'react'
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
  Legend,
} from 'recharts'

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

const TYPE_META = {
  contract: { label: 'Contracts', color: '#0066cc' },
  trade: { label: 'Trades', color: '#34c759' },
  stake: { label: 'Stakes', color: '#7a7a7a' },
  foreign_holding: { label: 'Foreign Holdings', color: '#af52de' },
}

const TYPE_ORDER = ['contract', 'stake', 'foreign_holding', 'trade']

function formatNumber(n) {
  if (n === undefined || n === null) return '—'
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(n)
}

function formatCurrency(n) {
  if (n === undefined || n === null) return '—'
  const abs = Math.abs(n)
  if (abs >= 1e12) return `$${(n / 1e12).toFixed(2)}T`
  if (abs >= 1e9) return `$${(n / 1e9).toFixed(2)}B`
  if (abs >= 1e6) return `$${(n / 1e6).toFixed(2)}M`
  if (abs >= 1e3) return `$${(n / 1e3).toFixed(2)}K`
  return `$${formatNumber(n)}`
}

function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return isNaN(d) ? iso : d.toLocaleDateString()
}

function useFetch(url) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        setLoading(true)
        const res = await fetch(url)
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
  }, [url])

  return { data, loading, error }
}

function SummaryCard({ label, value, subtext, tone = 'ink' }) {
  const toneClass = {
    ink: 'text-apple-ink',
    green: 'text-green-600',
    red: 'text-red-600',
    amber: 'text-amber-600',
  }[tone]
  return (
    <div className="apple-card-compact">
      <div className="apple-stat-label">{label}</div>
      <div className={`apple-stat-value ${toneClass} mt-1`}>{value}</div>
      {subtext && <div className="text-apple-caption text-apple-ink-muted-48 mt-0.5">{subtext}</div>}
    </div>
  )
}

function TypePie({ data }) {
  const chartData = data.map((d) => ({
    name: TYPE_META[d.event_type]?.label || d.event_type,
    value: d.total,
    color: TYPE_META[d.event_type]?.color || '#8e8e93',
  }))
  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="name"
            innerRadius={55}
            outerRadius={80}
            paddingAngle={2}
          >
            {chartData.map((d, i) => (
              <Cell key={i} fill={d.color} />
            ))}
          </Pie>
          <ReTooltip formatter={(value) => formatCurrency(value)} />
          <Legend verticalAlign="bottom" height={24} iconType="circle" />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

function TopTickersChart({ data }) {
  const chartData = data.slice(0, 10).map((d) => ({
    ticker: d.ticker,
    Contracts: d.contract_exposure,
    Stakes: d.stake_exposure,
    'Foreign Holdings': d.foreign_exposure,
    'Trade Net': d.trade_net_flow,
    total: d.total_exposure,
  }))
  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ top: 10, right: 20, left: 40, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e5e5" />
          <XAxis type="number" tick={{ fontSize: 12, fill: '#6e6e73' }} tickFormatter={(v) => formatCurrency(v)} />
          <YAxis type="category" dataKey="ticker" tick={{ fontSize: 12, fill: '#1d1d1f', fontWeight: 500 }} width={70} />
          <ReTooltip formatter={(value) => formatCurrency(value)} />
          <Legend verticalAlign="top" height={24} />
          <Bar dataKey="Contracts" stackId="a" fill={TYPE_META.contract.color} radius={[0, 0, 0, 0]} />
          <Bar dataKey="Stakes" stackId="a" fill={TYPE_META.stake.color} radius={[0, 0, 0, 0]} />
          <Bar dataKey="Foreign Holdings" stackId="a" fill={TYPE_META.foreign_holding.color} radius={[0, 0, 0, 0]} />
          <Bar dataKey="Trade Net" stackId="a" fill={TYPE_META.trade.color} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function ActivityTimeline({ data, mode }) {
  const pivoted = useMemo(() => {
    const map = new Map()
    data.forEach((d) => {
      const day = d.day?.split('T')[0]
      if (!day) return
      if (!map.has(day)) map.set(day, { day })
      map.get(day)[d.event_type] = mode === 'amount' ? d.amount : d.count
    })
    return Array.from(map.values()).sort((a, b) => a.day.localeCompare(b.day))
  }, [data, mode])

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={pivoted} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e5e5" />
          <XAxis dataKey="day" tick={{ fontSize: 12, fill: '#6e6e73' }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 12, fill: '#6e6e73' }} axisLine={false} tickLine={false} />
          <ReTooltip formatter={(value) => (mode === 'amount' ? formatCurrency(value) : formatNumber(value))} />
          <Legend verticalAlign="top" height={24} />
          {TYPE_ORDER.map((type) => (
            <Bar
              key={type}
              dataKey={type}
              name={TYPE_META[type].label}
              stackId="a"
              fill={TYPE_META[type].color}
              radius={[2, 2, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function ChangesTable({ title, rows, tone }) {
  if (!rows || rows.length === 0) return null
  return (
    <div className="apple-card p-5">
      <h4 className={`text-apple-body-strong mb-4 ${tone === 'red' ? 'text-red-600' : 'text-green-600'}`}>{title}</h4>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr>
              <th className="apple-table-header rounded-l-apple-lg">Ticker</th>
              <th className="apple-table-header text-right">Window Exposure</th>
              <th className="apple-table-header text-right">Window Events</th>
              <th className="apple-table-header text-right rounded-r-apple-lg">Current Exposure</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.ticker} className="border-b border-apple-hairline last:border-0">
                <td className="apple-table-cell font-medium">{r.ticker}</td>
                <td className="apple-table-cell text-right">{formatCurrency(r.window_exposure)}</td>
                <td className="apple-table-cell text-right">{formatNumber(r.window_event_count)}</td>
                <td className="apple-table-cell text-right">{formatCurrency(r.current_exposure)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function dominantType(row) {
  const entries = [
    { type: 'contract', value: row.contract_exposure },
    { type: 'stake', value: row.stake_exposure },
    { type: 'foreign_holding', value: row.foreign_exposure },
    { type: 'trade', value: Math.abs(row.trade_net_flow) },
  ]
  entries.sort((a, b) => b.value - a.value)
  return entries[0]
}

function buildSummary(snapshot, changes) {
  const totalEvents = snapshot.by_type.reduce((sum, t) => sum + t.count, 0)
  const sortedChannels = [...snapshot.by_type].sort((a, b) => b.total - a.total)
  const largest = sortedChannels[0]
  const second = sortedChannels[1]
  const topTicker = snapshot.top_tickers[0]
  const topDominant = topTicker ? dominantType(topTicker) : null

  const bullets = []

  bullets.push(
    `The unified portfolio carries **${formatCurrency(snapshot.total_exposure)}** of signed exposure ` +
      `(${formatCurrency(snapshot.gross_exposure)} gross) across **${formatNumber(totalEvents)}** government-public company signals.`
  )

  if (largest) {
    bullets.push(
      `The largest channel is **${TYPE_META[largest.event_type]?.label || largest.event_type}** ` +
        `(${formatCurrency(largest.total)}), followed by **${TYPE_META[second?.event_type]?.label || second?.event_type}** ` +
        `(${formatCurrency(second?.total || 0)}).`
    )
  }

  if (topTicker && topDominant) {
    bullets.push(
      `Concentration risk is highest in **${topTicker.ticker}** at **${formatCurrency(topTicker.total_exposure)}**, ` +
        `driven mainly by **${TYPE_META[topDominant.type]?.label || topDominant.type}** ` +
        `(${formatCurrency(topDominant.value)}).`
    )
  }

  if (snapshot.trade_net_flow !== 0) {
    const direction = snapshot.trade_net_flow > 0 ? 'net buying' : 'net selling'
    bullets.push(
      `Official trade flow shows **${direction}** pressure of **${formatCurrency(Math.abs(snapshot.trade_net_flow))}**, ` +
        `suggesting officials are ${direction === 'net buying' ? 'adding' : 'reducing'} exposure on average.`
    )
  }

  bullets.push(
    `Over the last **${changes.period_days} days**, **${formatNumber(changes.new_event_count)}** new events ` +
      `added **${formatCurrency(changes.new_exposure)}** of signed exposure.`
  )

  if (changes.top_gainers.length > 0) {
    const g = changes.top_gainers[0]
    bullets.push(`The largest recent exposure gainer is **${g.ticker}** (+${formatCurrency(g.window_exposure)}).`)
  }
  if (changes.top_losers.length > 0) {
    const l = changes.top_losers[0]
    bullets.push(`The largest recent exposure loser is **${l.ticker}** (${formatCurrency(l.window_exposure)}).`)
  }

  // Conclusion
  const stakeHeavy = sortedChannels.some((c) => c.event_type === 'stake' && c.total > (snapshot.gross_exposure * 0.3))
  const recentTradeHeavy = changes.by_type.some((c) => c.event_type === 'trade' && c.count > changes.new_event_count * 0.3)
  const conclusionParts = []
  if (stakeHeavy) conclusionParts.push('legacy bailouts/equity stakes dominate the book')
  if (recentTradeHeavy) conclusionParts.push('recent official trading is the main source of change')
  if (conclusionParts.length === 0) conclusionParts.push('contract awards are the primary driver of recent activity')

  bullets.push(
    `**Conclusion:** ${conclusionParts.join(' and ')}. ` +
      `Monitor ${changes.top_gainers.length > 0 ? changes.top_gainers[0].ticker : 'top tickers'} for follow-through and watch for fresh stake or foreign-holding filings, which tend to move the exposure needle the most.`
  )

  return bullets
}

function SummaryPanel({ snapshot, changes }) {
  const bullets = useMemo(() => buildSummary(snapshot, changes), [snapshot, changes])
  return (
    <div className="apple-card p-5 border-l-4 border-l-apple-primary">
      <h3 className="apple-section-title mb-4">Executive Summary</h3>
      <ul className="space-y-3 text-apple-body text-apple-ink">
        {bullets.map((text, idx) => (
          <li key={idx} className="leading-relaxed">
            <span className="font-medium text-apple-primary mr-2">{idx + 1}.</span>
            <span dangerouslySetInnerHTML={{ __html: text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function PortfolioAnalysis() {
  const [days, setDays] = useState(7)
  const [timelineMode, setTimelineMode] = useState('count')
  const snapshot = useFetch(`${API_BASE}/portfolio/snapshot?top_n=20`)
  const changes = useFetch(`${API_BASE}/portfolio/changes?days=${days}&top_n=10`)

  const loading = snapshot.loading || changes.loading
  const error = snapshot.error || changes.error
  const data = snapshot.data && changes.data ? { snapshot: snapshot.data, changes: changes.data } : null

  if (loading) {
    return (
      <div className="text-center py-20 text-apple-ink-muted-48 text-apple-body">Loading portfolio analysis…</div>
    )
  }

  if (error || !data) {
    return (
      <div className="text-center py-20 text-red-600 text-apple-body">
        Failed to load portfolio analysis: {error || 'unknown error'}
      </div>
    )
  }

  const { snapshot: snap, changes: chg } = data
  const netTone = snap.trade_net_flow >= 0 ? 'green' : 'red'
  const newTone = chg.new_exposure >= 0 ? 'green' : 'red'

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <h2 className="apple-section-title">Portfolio Analysis</h2>
          <p className="text-apple-caption text-apple-ink-muted-48 mt-1">
            Unified government-driven exposure across contracts, trades, stakes, and sovereign holdings.
          </p>
        </div>
        <div className="text-apple-caption text-apple-ink-muted-48">
          Snapshot as of {new Date(snap.as_of).toLocaleDateString()}
        </div>
      </div>

      {/* Snapshot summary */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard label="Total Exposure (signed)" value={formatCurrency(snap.total_exposure)} />
        <SummaryCard label="Gross Exposure" value={formatCurrency(snap.gross_exposure)} />
        <SummaryCard label="Trade Net Flow" value={formatCurrency(snap.trade_net_flow)} tone={netTone} />
        <SummaryCard
          label="Recent Change Exposure"
          value={formatCurrency(chg.new_exposure)}
          subtext={`${formatNumber(chg.new_event_count)} new events in last ${chg.period_days}d`}
          tone={newTone}
        />
      </div>

      {/* Executive summary */}
      <SummaryPanel snapshot={snap} changes={chg} />

      {/* Snapshot charts -->
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="apple-card p-6">
          <h3 className="apple-section-title mb-2">Exposure by Channel</h3>
          <TypePie data={snap.by_type} />
          <div className="mt-4 space-y-2">
            {snap.by_type.map((t) => (
              <div key={t.event_type} className="flex justify-between text-apple-caption">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: TYPE_META[t.event_type]?.color }} />
                  <span className="text-apple-ink">{TYPE_META[t.event_type]?.label || t.event_type}</span>
                </div>
                <span className="text-apple-ink-muted-48">{formatCurrency(t.total)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="apple-card p-6 lg:col-span-2">
          <h3 className="apple-section-title mb-3">Top 10 Tickers by Exposure</h3>
          <TopTickersChart data={snap.top_tickers} />
        </div>
      </div>

      {/* Activity timeline */}
      <div className="apple-card p-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
          <h3 className="apple-section-title">30-Day Activity</h3>
          <div className="flex rounded-apple-pill p-1 bg-apple-pearl border border-apple-divider-soft">
            <button
              onClick={() => setTimelineMode('count')}
              className={`px-4 py-1.5 rounded-apple-pill text-apple-caption transition-all ${
                timelineMode === 'count' ? 'bg-apple-primary text-white' : 'text-apple-ink hover:bg-apple-divider-soft'
              }`}
            >
              Event Count
            </button>
            <button
              onClick={() => setTimelineMode('amount')}
              className={`px-4 py-1.5 rounded-apple-pill text-apple-caption transition-all ${
                timelineMode === 'amount' ? 'bg-apple-primary text-white' : 'text-apple-ink hover:bg-apple-divider-soft'
              }`}
            >
              Notional Amount
            </button>
          </div>
        </div>
        <ActivityTimeline data={snap.activity_timeline} mode={timelineMode} />
      </div>

      {/* Changes section */}
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <h3 className="apple-section-title">Recent Changes</h3>
          <div className="flex rounded-apple-pill p-1 bg-apple-pearl border border-apple-divider-soft">
            {[7, 14, 30].map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-4 py-1.5 rounded-apple-pill text-apple-caption transition-all ${
                  days === d ? 'bg-apple-primary text-white' : 'text-apple-ink hover:bg-apple-divider-soft'
                }`}
              >
                Last {d}d
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <SummaryCard label="New Events" value={formatNumber(chg.new_event_count)} />
          <SummaryCard label="New Exposure" value={formatCurrency(chg.new_exposure)} tone={newTone} />
          <SummaryCard label="Trade Net Flow" value={formatCurrency(chg.trade_net_flow)} tone={chg.trade_net_flow >= 0 ? 'green' : 'red'} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChangesTable title="Top Exposure Gainers" rows={chg.top_gainers} tone="green" />
          <ChangesTable title="Top Exposure Losers" rows={chg.top_losers} tone="red" />
        </div>

        {/* Latest events */}
        <div className="apple-card p-5 overflow-hidden">
          <h3 className="apple-section-title mb-3">Latest Events in Period</h3>
          <div className="overflow-x-auto -mx-6 px-6">
            <table className="w-full min-w-[700px]">
              <thead>
                <tr>
                  <th className="apple-table-header rounded-l-apple-lg">Date</th>
                  <th className="apple-table-header">Type</th>
                  <th className="apple-table-header">Ticker</th>
                  <th className="apple-table-header">Company</th>
                  <th className="apple-table-header text-right">Amount</th>
                  <th className="apple-table-header rounded-r-apple-lg">Source / Party</th>
                </tr>
              </thead>
              <tbody>
                {chg.latest_events.map((ev) => (
                  <tr key={ev.id} className="border-b border-apple-hairline last:border-0">
                    <td className="apple-table-cell">{formatDate(ev.occurred_at)}</td>
                    <td className="apple-table-cell">
                      <span
                        className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-apple-pill text-apple-caption font-medium"
                        style={{
                          backgroundColor: `${TYPE_META[ev.event_type]?.color}15`,
                          color: TYPE_META[ev.event_type]?.color,
                        }}
                      >
                        {TYPE_META[ev.event_type]?.label || ev.event_type}
                      </span>
                    </td>
                    <td className="apple-table-cell font-medium">{ev.ticker || '—'}</td>
                    <td className="apple-table-cell max-w-[200px] truncate" title={ev.company_name}>
                      {ev.company_name || '—'}
                    </td>
                    <td className="apple-table-cell text-right">{formatCurrency(ev.amount)}</td>
                    <td className="apple-table-cell text-apple-ink-muted-48">{ev.government_party || ev.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
