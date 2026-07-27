import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, type Report, type School, type ReportPhoto } from '../api'
import { PHOTO_CATEGORIES, PHOTO_CATEGORY_LABELS, NOTE_CATEGORIES, NOTE_CATEGORY_LABELS } from '../constants'
import PhotoUploader from '../components/PhotoUploader'
import ChecklistSection from '../components/ChecklistSection'
import VisitInfoSection from '../components/VisitInfoSection'
import { showToast } from '../components/Toast'

export default function ReportEditor() {
  const { id } = useParams<{ id: string }>()
  const reportId = Number(id)
  const navigate = useNavigate()

  const [report, setReport] = useState<Report | null>(null)
  const [school, setSchool] = useState<School | null>(null)
  const [loading, setLoading] = useState(true)
  const [downloading, setDownloading] = useState(false)
  const [downloadingPdf, setDownloadingPdf] = useState(false)

  async function downloadReport() {
    if (!report || !school) return
    setDownloading(true)
    try {
      await api.downloadReport(report.id, `${school.name}_${report.visit_date}.pptx`)
      showToast('تم إصدار التقرير', 'success')
    } catch (err) {
      showToast('تعذّر إصدار التقرير، حاول مرة أخرى', 'error')
      console.error(err)
    } finally {
      setDownloading(false)
    }
  }

  async function downloadReportPdf() {
    if (!report || !school) return
    setDownloadingPdf(true)
    try {
      await api.downloadReportPdf(report.id, `${school.name}_${report.visit_date}.pdf`)
      showToast('تم إصدار نسخة PDF', 'success')
    } catch (err) {
      showToast('تعذّر إصدار نسخة PDF، حاول مرة أخرى', 'error')
      console.error(err)
    } finally {
      setDownloadingPdf(false)
    }
  }

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

      <VisitInfoSection
        reportId={report.id}
        initial={{
          contractor: report.contractor || '',
          visit_type: report.visit_type || '',
          during_readiness_plan: report.during_readiness_plan || '',
          team_count: report.team_count ?? null,
          oversight_supervisor_present: report.oversight_supervisor_present || '',
          team_types: report.team_types || '',
          important_notes: report.important_notes || '',
        }}
      />

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
        <button
          type="button"
          className="btn-primary sticky-cta"
          disabled={downloading}
          onClick={downloadReport}
        >
          {downloading ? 'جارٍ إصدار التقرير...' : 'إصدار التقرير (PPTX) — قابل للتعديل'}
        </button>
        <button
          type="button"
          className="btn-secondary"
          disabled={downloadingPdf}
          onClick={downloadReportPdf}
        >
          {downloadingPdf ? 'جارٍ إصدار PDF...' : 'إصدار نسخة PDF — للمشاركة الرسمية'}
        </button>
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
