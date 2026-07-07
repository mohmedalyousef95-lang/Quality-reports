import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, type Report, type School, type ReportPhoto } from '../api'
import { PHOTO_CATEGORIES, PHOTO_CATEGORY_LABELS, NOTE_CATEGORIES, NOTE_CATEGORY_LABELS } from '../constants'
import PhotoUploader from '../components/PhotoUploader'
import ChecklistSection from '../components/ChecklistSection'

export default function ReportEditor() {
  const { id } = useParams<{ id: string }>()
  const reportId = Number(id)
  const navigate = useNavigate()

  const [report, setReport] = useState<Report | null>(null)
  const [school, setSchool] = useState<School | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportId])

  async function load() {
    setLoading(true)
    try {
      const r = await api.getReport(reportId)
      setReport(r)
      const s = await api.getSchool(r.school_id)
      setSchool(s)
    } finally {
      setLoading(false)
    }
  }

  function updatePhotos(category: string, photos: ReportPhoto[]) {
    setReport((prev) => {
      if (!prev) return prev
      const otherPhotos = prev.photos.filter((p) => p.category !== category)
      return { ...prev, photos: [...otherPhotos, ...photos] }
    })
  }

  if (loading || !report || !school) {
    return <div className="page">جارٍ التحميل...</div>
  }

  return (
    <div className="page">
      <div className="report-header">
        <h1 className="page-title">{school.name}</h1>
        <div className="report-meta">
          {report.visit_date} · {report.visitor_name}
        </div>
      </div>

      <section className="section-block">
        <h2>الصور</h2>
        {PHOTO_CATEGORIES.map((category) => (
          <PhotoUploader
            key={category}
            reportId={report.id}
            category={category}
            label={PHOTO_CATEGORY_LABELS[category]}
            photos={report.photos.filter((p) => p.category === category)}
            onChange={(photos) => updatePhotos(category, photos)}
          />
        ))}
      </section>

      <section className="section-block">
        <h2>الملاحظات</h2>
        {NOTE_CATEGORIES.map((category) => (
          <ChecklistSection
            key={category}
            reportId={report.id}
            category={category}
            label={NOTE_CATEGORY_LABELS[category]}
            initialNotes={report.notes.filter((n) => n.category === category)}
          />
        ))}
      </section>

      <div className="report-actions">
        <a className="btn-primary sticky-cta" href={api.downloadUrl(report.id)}>
          إصدار التقرير (PPTX)
        </a>
        <button
          type="button"
          className="link-button"
          onClick={() => navigate(`/schools/${school.ministry_number}`)}
        >
          العودة لسجل المدرسة
        </button>
      </div>
    </div>
  )
}
