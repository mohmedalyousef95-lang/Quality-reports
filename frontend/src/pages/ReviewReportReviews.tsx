import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, type Report, type School, type ReviewListItem } from '../api'
import { showToast } from '../components/Toast'

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

export default function ReviewReportReviews() {
  const { reportId } = useParams<{ reportId: string }>()
  const id = Number(reportId)
  const navigate = useNavigate()

  const [report, setReport] = useState<Report | null>(null)
  const [school, setSchool] = useState<School | null>(null)
  const [reviews, setReviews] = useState<ReviewListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    if (!id) return
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  async function load() {
    setLoading(true)
    const r = await api.getReport(id)
    setReport(r)
    const [s, rv] = await Promise.all([api.getSchool(r.school_id), api.getReportReviews(id)])
    setSchool(s)
    setReviews(rv)
    setLoading(false)
  }

  async function startReview() {
    setCreating(true)
    try {
      const review = await api.createReview({
        report_id: id,
        visit_date: today(),
        visitor_name: localStorage.getItem('lastVisitorName') || '',
      })
      navigate(`/reviews/${review.id}`)
    } catch {
      showToast('تعذّر إنشاء المراجعة، حاول مرة أخرى', 'error')
    } finally {
      setCreating(false)
    }
  }

  if (loading || !report || !school) {
    return <div className="page">جارٍ التحميل...</div>
  }

  return (
    <div className="page">
      <h1 className="page-title">{school.name}</h1>
      <div className="page-subtitle">
        التقرير الأصلي بتاريخ {report.visit_date} · {report.visitor_name}
      </div>

      <button type="button" className="btn-primary sticky-cta" disabled={creating} onClick={startReview}>
        {creating ? 'جارٍ الإنشاء...' : '+ بدء مراجعة جديدة'}
      </button>

      <h2 className="section-title">المراجعات السابقة</h2>
      {reviews.length === 0 && <div className="empty-hint">لا توجد مراجعات سابقة لهذا التقرير</div>}
      <ul className="report-list">
        {reviews.map((rv) => (
          <li key={rv.id} className="report-list-item">
            <div>
              <div className="report-list-date">{rv.visit_date}</div>
              <div className="report-list-visitor">{rv.visitor_name}</div>
              <span className={`status-badge status-${rv.status}`}>
                {rv.status === 'completed' ? 'مكتملة' : 'مسودة'}
              </span>
            </div>
            <div className="report-list-actions">
              <button type="button" className="link-button" onClick={() => navigate(`/reviews/${rv.id}`)}>
                فتح
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
