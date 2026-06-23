import { useState, useRef, useEffect } from 'react'

export default function FilterDropdown({ label, options, selected, onChange, placeholder = 'All' }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    function handleClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const toggle = (value) => {
    if (selected.includes(value)) {
      onChange(selected.filter((v) => v !== value))
    } else {
      onChange([...selected, value])
    }
  }

  const clearAll = () => onChange([])

  const summary =
    selected.length === 0
      ? placeholder
      : `${selected.length} selected`

  return (
    <div className="relative" ref={ref}>
      {label && <span className="text-apple-caption text-apple-ink-muted-48 mr-2">{label}</span>}
      <button
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center justify-between gap-3 bg-apple-canvas text-apple-ink border border-apple-hairline rounded-apple-pill px-4 py-2 text-apple-caption hover:bg-apple-pearl focus:outline-none focus:ring-2 focus:ring-apple-primary-focus h-[38px] min-w-[150px]"
      >
        <span className="truncate">{summary}</span>
        <span className="text-apple-ink-muted-48 text-xs">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div
          className="absolute right-0 mt-2 w-72 max-h-96 overflow-y-auto apple-card z-20 p-3"
          onMouseDown={(e) => e.stopPropagation()}
        >
          <div className="flex justify-between items-center mb-2 px-2">
            <span className="text-apple-caption-strong text-apple-ink">{label || 'Select'}</span>
            {selected.length > 0 && (
              <button
                onClick={clearAll}
                className="text-apple-primary text-apple-caption hover:underline"
              >
                Clear all
              </button>
            )}
          </div>
          {options.map((option) => {
            const value = typeof option === 'string' ? option : option.value
            const text = typeof option === 'string' ? option : option.label
            return (
              <label
                key={value}
                className="flex items-center px-2 py-2 hover:bg-apple-parchment rounded-apple-sm cursor-pointer text-apple-body"
              >
                <input
                  type="checkbox"
                  checked={selected.includes(value)}
                  onChange={() => toggle(value)}
                  className="mr-3 h-4 w-4 accent-apple-primary rounded border-apple-hairline"
                />
                <span className="truncate" title={text}>{text}</span>
              </label>
            )
          })}
        </div>
      )}
    </div>
  )
}
