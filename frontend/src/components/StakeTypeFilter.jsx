import FilterDropdown from './FilterDropdown'

const STAKE_TYPES = [
  { value: 'warrant', label: 'Warrant' },
  { value: 'preferred_stock', label: 'Preferred Stock' },
  { value: 'common_stock', label: 'Common Stock' },
  { value: 'loan', label: 'Loan' },
  { value: 'bailout', label: 'Bailout' },
  { value: 'direct_investment', label: 'Direct Investment' },
  { value: 'other', label: 'Other' },
]

export default function StakeTypeFilter({ selected, onChange }) {
  return (
    <FilterDropdown
      label="Stake Type:"
      options={STAKE_TYPES}
      selected={selected}
      onChange={onChange}
      placeholder="All stake types"
    />
  )
}
