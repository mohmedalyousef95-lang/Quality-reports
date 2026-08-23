import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, type School, type ReportListItem } from '../api'

export default function ReviewSchoolReports() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [school, setSchool] = useState<School | null>(null)
  const [reports, setReports] = useState<ReportListItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    Promise.all([api.getSchool(id), api.getSchoolReports(id)]).then(([s, r]) => {
      setSchool(s)
      setReports(r)
      setLoading(false)
    })
  }, [id])

  if (loading || !school) {
    return <div className="page">جارٍ التحميل...</div>
  }

  return (
    <div className="page">
      <h1 className="page-title">{school.name}</h1>
      <div className="page-subtitle">اختر التقرير المطلوب مراجعته</div>

      {reports.length === 0 && <div className="empty-hint">لا توجد تقارير سابقة لهذه المدرسة</div>}
      <ul className="report-list">
        {reports.map((r) => (
          <li
            key={r.id}
            className="report-list-item clickable"
            onClick={() => navigate(`/reviews/reports/${r.id}`)}
          >
            <div>
              <div className="report-list-date">{r.visit_date}</div>
              <div className="report-list-visitor">{r.visitor_name}</div>
            </div>
            <span className="report-list-actions">‹</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
