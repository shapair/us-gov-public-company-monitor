import FilterDropdown from './FilterDropdown'

const FILING_TYPES = [
  { value: '13F-HR', label: '13F-HR' },
  { value: '13F-HR/A', label: '13F-HR/A' },
  { value: '13D', label: '13D' },
  { value: '13D/A', label: '13D/A' },
  { value: '13G', label: '13G' },
  { value: '13G/A', label: '13G/A' },
]

export default function FilingTypeFilter({ selected, onChange }) {
  return (
    <FilterDropdown
      label="Filing type"
      options={FILING_TYPES}
      selected={selected}
      onChange={onChange}
      placeholder="All types"
    />
  )
}
