import FilterDropdown from './FilterDropdown'

const TYPES = [
  { value: 'purchase', label: 'Purchase' },
  { value: 'sale', label: 'Sale' },
  { value: 'exchange', label: 'Exchange' },
  { value: 'other', label: 'Other' },
]

export default function TransactionTypeFilter({ selected, onChange }) {
  return (
    <FilterDropdown
      label="Type:"
      options={TYPES}
      selected={selected}
      onChange={onChange}
      placeholder="All types"
    />
  )
}
