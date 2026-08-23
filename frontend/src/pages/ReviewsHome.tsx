import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type SchoolReviewSummary } from '../api'

const OVERDUE_DAYS = 20

function daysSince(dateStr: string): number {
  const then = new Date(dateStr + 'T00:00:00')
  const now = new Date()
  return Math.floor((now.getTime() - then.getTime()) / (1000 * 60 * 60 * 24))
}

export default function ReviewsHome() {
  const [schools, setSchools] = useState<SchoolReviewSummary[]>([])
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    api
      .getSchoolsWithReports()
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
      <div className="page-subtitle">
        المدارس التي صدرت لها تقارير جودة، مرتبة من الأحدث — العلامة الحمراء تعني تجاوز آخر
        تقرير {OVERDUE_DAYS} يومًا دون مراجعة
      </div>

      <input
        type="text"
        className="input"
        placeholder="فلترة باسم المدرسة أو الرقم الوزاري"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
      />

      {loading && <div className="empty-hint">جارٍ التحميل...</div>}
      {!loading && visible.length === 0 && (
        <div className="empty-hint">لا توجد مدارس صدرت لها تقارير جودة بعد</div>
      )}

      <ul className="report-list">
        {visible.map((school) => {
          const overdue = daysSince(school.latest_visit_date) > OVERDUE_DAYS
          return (
            <li
              key={school.ministry_number}
              className="report-list-item clickable"
              onClick={() => navigate(`/reviews/schools/${school.ministry_number}`)}
            >
              <div>
                <div className="report-list-visitor">
                  {overdue && <span className="overdue-dot" title={`متأخر أكثر من ${OVERDUE_DAYS} يومًا`} />}
                  {school.name}
                </div>
                <div className="report-list-date">
                  آخر تقرير: {school.latest_visit_date} · {school.zone}
                </div>
              </div>
              <span className="report-list-actions">‹</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
