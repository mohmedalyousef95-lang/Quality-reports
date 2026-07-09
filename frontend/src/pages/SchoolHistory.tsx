import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, type School, type ReportListItem } from '../api'

export default function SchoolHistory() {
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

  async function startNewReport() {
    if (!school) return
    const report = await api.createReport({
      school_id: school.ministry_number,
      visit_date: new Date().toISOString().slice(0, 10),
      visitor_name: localStorage.getItem('lastVisitorName') || '',
    })
    navigate(`/reports/${report.id}`)
  }

  if (loading || !school) {
    return <div className="page">جارٍ التحميل...</div>
  }

  return (
    <div className="page">
      <h1 className="page-title">{school.name}</h1>
      <div className="school-card">
        <div className="school-card-row">
          <span>الزون</span>
          <span>{school.zone}</span>
        </div>
        <div className="school-card-row">
          <span>المهندس</span>
          <span>{school.engineer}</span>
        </div>
        <div className="school-card-row">
          <span>المشرف</span>
          <span>{school.supervisor}</span>
        </div>
        <div className="school-card-row">
          <span>العنوان</span>
          <span>{school.address}</span>
        </div>
      </div>

      <button type="button" className="btn-primary" onClick={startNewReport}>
        زيارة جديدة
      </button>

      <h2 className="section-title">سجل الزيارات</h2>
      {reports.length === 0 && <div className="empty-hint">لا توجد زيارات سابقة</div>}
      <ul className="report-list">
        {reports.map((r) => (
          <li key={r.id} className="report-list-item">
            <div>
              <div className="report-list-date">{r.visit_date}</div>
              <div className="report-list-visitor">{r.visitor_name}</div>
            </div>
            <div className="report-list-actions">
              <button
                type="button"
                className="link-button"
                onClick={() => navigate(`/reports/${r.id}`)}
              >
                فتح
              </button>
              <button
                type="button"
                className="link-button"
                onClick={() =>
                  api.downloadReport(r.id, `${school.name}_${r.visit_date}.pptx`)
                }
              >
                تنزيل
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
