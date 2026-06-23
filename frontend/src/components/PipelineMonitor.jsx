import { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'

const STATUS_STYLES = {
  healthy: { badge: 'bg-green-100 text-green-700', dot: 'bg-green-500', icon: '●' },
  stale: { badge: 'bg-red-100 text-red-700', dot: 'bg-red-500', icon: '●' },
  warning: { badge: 'bg-amber-100 text-amber-700', dot: 'bg-amber-500', icon: '●' },
  idle: { badge: 'bg-gray-100 text-gray-600', dot: 'bg-gray-400', icon: '○' },
  unknown: { badge: 'bg-gray-100 text-gray-600', dot: 'bg-gray-400', icon: '?' },
  info: { badge: 'bg-blue-100 text-blue-700', dot: 'bg-blue-500', icon: '●' },
}

const FREQUENCY_LABELS = {
  daily: 'Daily',
  monthly: 'Monthly',
}

function formatNumber(n) {
  if (n === undefined || n === null) return '—'
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(n)
}

function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return isNaN(d) ? iso : d.toLocaleString()
}

function formatDateShort(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return isNaN(d) ? iso : d.toLocaleDateString()
}

function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.unknown
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-apple-pill text-apple-caption font-medium ${style.badge}`}
    >
      <span className={`w-2 h-2 rounded-full ${style.dot}`} />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

export default function PipelineMonitor() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        setLoading(true)
        const res = await fetch(`${API_BASE}/dashboard/pipelines`)
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
        Loading pipeline monitor…
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="text-center py-20 text-red-600 text-apple-body">
        Failed to load pipeline monitor: {error || 'unknown error'}
      </div>
    )
  }

  const overallStyle = STATUS_STYLES[data.overall_status] || STATUS_STYLES.unknown

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <h2 className="apple-section-title">Pipeline Monitor</h2>
          <p className="text-apple-caption text-apple-ink-muted-48 mt-1">
            Generated at {new Date(data.generated_at).toLocaleString()}
          </p>
        </div>
        <div className="apple-card px-5 py-3 flex items-center gap-4">
          <div>
            <div className="text-apple-caption text-apple-ink-muted-48">Overall Status</div>
            <div className={`text-[28px] leading-none font-display ${overallStyle.badge.split(' ')[1]}`}>
              {data.overall_status.charAt(0).toUpperCase() + data.overall_status.slice(1)}
            </div>
          </div>
          <div className="h-10 w-px bg-apple-hairline" />
          <div>
            <div className="text-apple-caption text-apple-ink-muted-48">Pipelines</div>
            <div className="text-[24px] leading-none font-display text-apple-ink">
              {formatNumber(data.pipelines?.length)}
            </div>
          </div>
        </div>
      </div>

      {/* Pipeline cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {data.pipelines.map((p) => (
          <div key={p.id} className="apple-card p-5 flex flex-col gap-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-apple-body-strong text-apple-ink">{p.name}</h3>
                <p className="text-apple-caption text-apple-ink-muted-48 font-mono mt-0.5">{p.id}</p>
              </div>
              <StatusBadge status={p.status} />
            </div>

            <div className="grid grid-cols-2 gap-3 text-apple-caption">
              <div className="p-3 rounded-apple-lg bg-apple-pearl/50">
                <div className="text-apple-ink-muted-48">Frequency</div>
                <div className="font-medium text-apple-ink mt-0.5">
                  {FREQUENCY_LABELS[p.frequency] || p.frequency}
                </div>
              </div>
              <div className="p-3 rounded-apple-lg bg-apple-pearl/50">
                <div className="text-apple-ink-muted-48">Events</div>
                <div className="font-medium text-apple-ink mt-0.5">{formatNumber(p.event_count)}</div>
              </div>
              <div className="p-3 rounded-apple-lg bg-apple-pearl/50">
                <div className="text-apple-ink-muted-48">Next Run</div>
                <div className="font-medium text-apple-ink mt-0.5">{formatDateShort(p.next_run_at)}</div>
                <div className="text-apple-micro text-apple-ink-muted-48 mt-0.5">
                  {p.next_run_at ? new Date(p.next_run_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
                </div>
              </div>
              <div className="p-3 rounded-apple-lg bg-apple-pearl/50">
                <div className="text-apple-ink-muted-48">Last Ingested</div>
                <div className="font-medium text-apple-ink mt-0.5">{formatDateShort(p.last_ingested_at)}</div>
                <div className="text-apple-micro text-apple-ink-muted-48 mt-0.5">
                  {p.last_ingested_at ? new Date(p.last_ingested_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-apple-hairline">
              <div className="flex justify-between text-apple-caption mb-1">
                <span className="text-apple-ink-muted-48">Latest data date</span>
                <span className="text-apple-ink">{formatDateShort(p.latest_data_at)}</span>
              </div>
              <div className="text-apple-caption text-apple-ink-muted-48 mt-2">{p.message}</div>
              <div className="text-apple-micro text-apple-ink-muted-48 mt-2 font-mono break-all">
                {p.schedule}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
