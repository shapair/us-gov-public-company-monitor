import { useEffect, useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

function formatCurrency(n) {
  if (n === undefined || n === null) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(n)
}

function formatCompact(n) {
  if (n === undefined || n === null) return '—'
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    compactDisplay: 'short',
    maximumFractionDigits: 1,
  }).format(n)
}

export default function TickerBarChart({ year, agencies = [], limit = 20 }) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams({ limit: String(limit) })
        if (year) params.set('year', String(year))
        agencies.forEach((agency) => params.append('agency', agency))
        const res = await fetch(`${API_BASE}/contracts/stats/by-ticker?${params}`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = await res.json()
        const sorted = (json || []).sort((a, b) => b.total_amount - a.total_amount)
        setData(sorted)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [year, agencies, limit])

  if (loading) return <div className="apple-card p-10 text-apple-ink-muted-48 text-apple-body">Loading chart…</div>
  if (error) return <div className="apple-card p-10 text-apple-primary text-apple-body">Failed to load chart: {error}</div>
  if (data.length === 0) return <div className="apple-card p-10 text-apple-ink-muted-48 text-apple-body">No data available.</div>

  const title = year ? `Top Tickers by Contract Value — ${year}` : 'Top Tickers by Contract Value'

  return (
    <div className="apple-card p-6">
      <h3 className="apple-section-title mb-1">{title}</h3>
      <div className="h-96 mt-5">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 60, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e0e0e0" />
            <XAxis
              type="number"
              tickFormatter={formatCompact}
              domain={[0, 'auto']}
              tick={{ fill: '#7a7a7a', fontSize: 12 }}
              axisLine={{ stroke: '#e0e0e0' }}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="ticker"
              width={80}
              tick={{ fill: '#1d1d1f', fontSize: 13, fontWeight: 500 }}
              interval={0}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              cursor={{ fill: '#f5f5f7' }}
              contentStyle={{
                backgroundColor: '#ffffff',
                border: '1px solid #e0e0e0',
                borderRadius: '18px',
                padding: '12px 16px',
                fontSize: '14px',
                color: '#1d1d1f',
                boxShadow: 'none',
              }}
              formatter={(value) => [formatCurrency(value), 'Amount']}
              labelFormatter={(label) => `Ticker: ${label}`}
            />
            <Bar dataKey="total_amount" fill="#0066cc" radius={[0, 8, 8, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
