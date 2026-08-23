import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type School } from '../api'

export default function ReviewsHome() {
  const [schools, setSchools] = useState<School[]>([])
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    api
      .searchSchools('', 500)
      .then(setSchools)
      .finally(() => setLoading(false))
  }, [])

  const visible = filter.trim()
    ? schools.filter(
        (s) => s.name.includes(filter.trim()) || s.ministry_number.includes(filter.trim()),
      )
    : schools

  return (
    <div className="page">
      <h1 className="page-title">تقارير المراجعة</h1>
      <div className="page-subtitle">اختر مدرسة لعرض تقاريرها السابقة وبدء مراجعة</div>

      <input
        type="text"
        className="input"
        placeholder="فلترة باسم المدرسة أو الرقم الوزاري"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
      />

      {loading && <div className="empty-hint">جارٍ التحميل...</div>}
      {!loading && visible.length === 0 && <div className="empty-hint">لا توجد مدارس مطابقة</div>}

      <ul className="report-list">
        {visible.map((school) => (
          <li
            key={school.ministry_number}
            className="report-list-item clickable"
            onClick={() => navigate(`/reviews/schools/${school.ministry_number}`)}
          >
            <div>
              <div className="report-list-visitor">{school.name}</div>
              <div className="report-list-date">
                {school.zone} · {school.ministry_number}
              </div>
            </div>
            <span className="report-list-actions">‹</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
