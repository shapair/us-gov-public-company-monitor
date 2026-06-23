import { useEffect, useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
  ReferenceLine,
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

export default function OfficialTradesNetChart({ chambers = [], limit = 20 }) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams({ limit: String(limit) })
        chambers.forEach((c) => params.append('chamber', c))
        const res = await fetch(`${API_BASE}/trades/stats/net-by-ticker?${params}`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = await res.json()
        setData((json || []).sort((a, b) => Math.abs(b.net) - Math.abs(a.net)))
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [chambers, limit])

  if (loading) return <div className="apple-card p-10 text-apple-ink-muted-48 text-apple-body">Loading chart…</div>
  if (error) return <div className="apple-card p-10 text-apple-primary text-apple-body">Failed to load chart: {error}</div>
  if (data.length === 0) return <div className="apple-card p-10 text-apple-ink-muted-48 text-apple-body">No trade data available.</div>

  return (
    <div className="apple-card p-6">
      <h3 className="apple-section-title mb-1">Net Purchase vs Sale Flow by Ticker</h3>
      <p className="text-apple-caption text-apple-ink-muted-48 mt-1">
        Positive = net purchases · Negative = net sales
      </p>
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
              domain={['auto', 'auto']}
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
              content={({ active, payload, label }) => {
                if (!active || !payload || !payload.length) return null
                const { purchase, sale, net, purchase_count, sale_count } = payload[0].payload
                return (
                  <div className="bg-apple-canvas border border-apple-hairline rounded-apple-lg p-4 text-apple-body">
                    <div className="font-display text-apple-body-strong mb-1">{label}</div>
                    <div className="text-[#34c759]">
                      Purchases: {formatCurrency(purchase)} ({purchase_count})
                    </div>
                    <div className="text-[#ff3b30]">
                      Sales: {formatCurrency(sale)} ({sale_count})
                    </div>
                    <div className="border-t border-apple-hairline mt-2 pt-2 font-medium">
                      Net: {formatCurrency(net)}
                    </div>
                  </div>
                )
              }}
            />
            <ReferenceLine x={0} stroke="#d2d2d7" />
            <Bar dataKey="net" radius={[0, 8, 8, 0]}>
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.net >= 0 ? '#34c759' : '#ff3b30'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
