import { useEffect, useRef, useState } from 'react'
import { api, type School } from '../api'

type Props = {
  onSelect: (school: School) => void
}

export default function SchoolAutocomplete({ onSelect }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<School[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const timerRef = useRef<number | undefined>(undefined)

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([])
      return
    }
    window.clearTimeout(timerRef.current)
    timerRef.current = window.setTimeout(async () => {
      setLoading(true)
      try {
        const schools = await api.searchSchools(query.trim())
        setResults(schools)
        setOpen(true)
      } finally {
        setLoading(false)
      }
    }, 250)
    return () => window.clearTimeout(timerRef.current)
  }, [query])

  return (
    <div className="autocomplete">
      <input
        type="text"
        className="input"
        placeholder="ابحث باسم المدرسة أو الرقم الوزاري"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => results.length > 0 && setOpen(true)}
      />
      {loading && <div className="autocomplete-hint">جارٍ البحث...</div>}
      {open && results.length > 0 && (
        <ul className="autocomplete-list">
          {results.map((school) => (
            <li
              key={school.ministry_number}
              onClick={() => {
                onSelect(school)
                setQuery(school.name)
                setOpen(false)
              }}
            >
              <div className="school-name">{school.name}</div>
              <div className="school-meta">
                {school.zone} · {school.ministry_number}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
