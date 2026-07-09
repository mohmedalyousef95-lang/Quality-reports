import { useEffect, useRef, useState } from 'react'
import { api, type School } from '../api'
import { showToast } from './Toast'

type Props = {
  onSelect: (school: School) => void
}

export default function SchoolAutocomplete({ onSelect }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<School[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [locating, setLocating] = useState(false)
  const [nearbyMode, setNearbyMode] = useState(false)
  const timerRef = useRef<number | undefined>(undefined)

  useEffect(() => {
    if (nearbyMode) return
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
  }, [query, nearbyMode])

  function findNearest() {
    if (!navigator.geolocation) {
      showToast('تحديد الموقع غير مدعوم في هذا المتصفح', 'error')
      return
    }
    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const schools = await api.nearbySchools(pos.coords.latitude, pos.coords.longitude)
          setResults(schools)
          setNearbyMode(true)
          setOpen(true)
          if (schools.length === 0) showToast('لا توجد مدارس قريبة', 'info')
        } catch {
          showToast('تعذّر جلب المدارس القريبة', 'error')
        } finally {
          setLocating(false)
        }
      },
      () => {
        showToast('تعذّر تحديد موقعك — تأكد من صلاحية الموقع', 'error')
        setLocating(false)
      },
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }

  return (
    <div className="autocomplete">
      <input
        type="text"
        className="input"
        placeholder="ابحث باسم المدرسة أو الرقم الوزاري"
        value={query}
        onChange={(e) => {
          setNearbyMode(false)
          setQuery(e.target.value)
        }}
        onFocus={() => results.length > 0 && setOpen(true)}
      />
      <button type="button" className="nearest-btn" onClick={findNearest} disabled={locating}>
        {locating ? 'جارٍ تحديد موقعك...' : '📍 أقرب المدارس لموقعي'}
      </button>

      {loading && <div className="autocomplete-hint">جارٍ البحث...</div>}
      {nearbyMode && open && (
        <div className="autocomplete-hint">المدارس مرتبة حسب قربها منك</div>
      )}
      {open && results.length > 0 && (
        <ul className="autocomplete-list">
          {results.map((school) => (
            <li
              key={school.ministry_number}
              onClick={() => {
                onSelect(school)
                setQuery(school.name)
                setNearbyMode(false)
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
