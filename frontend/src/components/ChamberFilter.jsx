import FilterDropdown from './FilterDropdown'

const CHAMBERS = [
  { value: 'house', label: 'House' },
  { value: 'senate', label: 'Senate' },
  { value: 'executive', label: 'Executive' },
]

export default function ChamberFilter({ selected, onChange }) {
  return (
    <FilterDropdown
      label="Chamber:"
      options={CHAMBERS}
      selected={selected}
      onChange={onChange}
      placeholder="All chambers"
    />
  )
}
