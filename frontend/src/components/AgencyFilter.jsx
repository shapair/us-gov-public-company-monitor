import FilterDropdown from './FilterDropdown'

export default function AgencyFilter({ agencies, selected, onChange }) {
  return (
    <FilterDropdown
      label="Agency:"
      options={agencies}
      selected={selected}
      onChange={onChange}
      placeholder="All agencies"
    />
  )
}
