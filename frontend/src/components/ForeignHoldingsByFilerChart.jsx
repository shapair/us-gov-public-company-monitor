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

function formatCompact(n) {
  if (n === undefined || n === null) return '—'
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    compactDisplay: 'short',
    maximumFractionDigits: 1,
  }).format(n)
}

function truncate(value, max = 24) {
  if (!value) return ''
  return value.length > max ? `${value.slice(0, max)}…` : value
}

export default function ForeignHoldingsByFilerChart({ filingTypes = [], limit = 20 }) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams({ limit: String(limit) })
        filingTypes.forEach((t) => params.append('filing_type', t))
        const res = await fetch(`${API_BASE}/foreign-holdings/stats/by-filer?${params}`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = await res.json()
        setData((json || []).sort((a, b) => b.total_amount - a.total_amount))
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [filingTypes, limit])

  if (loading) return <div className="apple-card p-10 text-apple-ink-muted-48 text-apple-body">Loading chart…</div>
  if (error) return <div className="apple-card p-10 text-apple-primary text-apple-body">Failed to load chart: {error}</div>
  if (data.length === 0) return <div className="apple-card p-10 text-apple-ink-muted-48 text-apple-body">No filer data available.</div>

  return (
    <div className="apple-card p-6">
      <h3 className="apple-section-title mb-1">Top Filers by Total Holding Value</h3>
      <div className="h-96 mt-5">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 120, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e0e0e0" />
            <XAxis
              type="number"
              tickFormatter={formatCompact}
              tick={{ fill: '#7a7a7a', fontSize: 12 }}
              axisLine={{ stroke: '#e0e0e0' }}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="filer_name"
              width={110}
              tick={{ fill: '#1d1d1f', fontSize: 12, fontWeight: 500 }}
              interval={0}
              axisLine={false}
              tickLine={false}
              tickFormatter={(value) => truncate(value, 18)}
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
              formatter={(value) => [formatCompact(value), 'Total value']}
              labelFormatter={(label) => `Filer: ${label}`}
            />
            <Bar dataKey="total_amount" fill="#af52de" radius={[0, 8, 8, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
