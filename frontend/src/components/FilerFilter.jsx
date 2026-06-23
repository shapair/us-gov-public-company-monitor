import FilterDropdown from './FilterDropdown'

export default function FilerFilter({ filers, selected, onChange }) {
  const options = (filers || []).map((f) => ({ value: f, label: f }))
  return (
    <FilterDropdown
      label="Filer"
      options={options}
      selected={selected}
      onChange={onChange}
      placeholder="All filers"
    />
  )
}
