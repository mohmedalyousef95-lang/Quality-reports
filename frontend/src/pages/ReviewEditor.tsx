import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, type Review, type ReviewNote } from '../api'
import {
  PHOTO_CATEGORIES,
  PHOTO_CATEGORY_LABELS,
  NOTE_CATEGORIES,
  NOTE_CATEGORY_LABELS,
  REVIEW_RESPONSE_OPTIONS,
} from '../constants'
import ReviewPhotoUploader from '../components/ReviewPhotoUploader'
import { showToast } from '../components/Toast'

export default function ReviewEditor() {
  const { id } = useParams<{ id: string }>()
  const reviewId = Number(id)

  const [review, setReview] = useState<Review | null>(null)
  const [loading, setLoading] = useState(true)
  const [downloading, setDownloading] = useState(false)
  const [downloadingPdf, setDownloadingPdf] = useState(false)
  const [visitDate, setVisitDate] = useState('')
  const [visitorName, setVisitorName] = useState('')
  const infoTimer = useRef<number | undefined>(undefined)

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reviewId])

  async function load() {
    setLoading(true)
    try {
      const r = await api.getReview(reviewId)
      setReview(r)
      setVisitDate(r.visit_date)
      setVisitorName(r.visitor_name || '')
    } finally {
      setLoading(false)
    }
  }

  function scheduleInfoSave(nextDate: string, nextVisitor: string) {
    window.clearTimeout(infoTimer.current)
    infoTimer.current = window.setTimeout(() => {
      api.updateReviewInfo(reviewId, { visit_date: nextDate, visitor_name: nextVisitor }).catch(() => {
        showToast('تعذّر حفظ بيانات الزيارة', 'error')
      })
    }, 500)
  }

  async function updateNote(note: ReviewNote, patch: Partial<ReviewNote>) {
    if (!review) return
    const merged = { ...note, ...patch }
    setReview({
      ...review,
      notes: review.notes.map((n) => (n.id === note.id ? merged : n)),
    })
    try {
      await api.updateReviewNote(reviewId, note.id, {
        note: merged.note,
        response_status: merged.response_status,
      })
    } catch {
      showToast('تعذّر حفظ الملاحظة', 'error')
    }
  }

  async function addNote(category: string, item: string) {
    if (!item.trim()) return
    try {
      const updated = await api.addReviewNote(reviewId, { category, item: item.trim() })
      setReview(updated)
    } catch {
      showToast('تعذّر إضافة الملاحظة', 'error')
    }
  }

  async function removeNote(noteId: number) {
    try {
      const updated = await api.deleteReviewNote(reviewId, noteId)
      setReview(updated)
    } catch {
      showToast('تعذّر حذف الملاحظة', 'error')
    }
  }

  async function downloadPptx() {
    if (!review) return
    setDownloading(true)
    try {
      await api.downloadReview(review.id, `مراجعة_${review.report.school_id}_${review.visit_date}.pptx`)
      showToast('تم إصدار تقرير المراجعة', 'success')
    } catch {
      showToast('تعذّر إصدار التقرير، حاول مرة أخرى', 'error')
    } finally {
      setDownloading(false)
    }
  }

  async function downloadPdf() {
    if (!review) return
    setDownloadingPdf(true)
    try {
      await api.downloadReviewPdf(review.id, `مراجعة_${review.report.school_id}_${review.visit_date}.pdf`)
      showToast('تم إصدار نسخة PDF', 'success')
    } catch {
      showToast('تعذّر إصدار نسخة PDF، حاول مرة أخرى', 'error')
    } finally {
      setDownloadingPdf(false)
    }
  }

  if (loading || !review) {
    return <div className="page">جارٍ التحميل...</div>
  }

  const total = review.notes.length
  const resolved = review.notes.filter((n) => n.response_status === 'تمت المعالجة').length
  const rate = total ? Math.round((resolved / total) * 100) : 0

  return (
    <div className="page">
      <div className="report-header">
        <h1 className="page-title">مراجعة متابعة</h1>
        <div className="report-meta">
          التقرير الأصلي: {review.report.visit_date} · {review.report.visitor_name}
        </div>
      </div>

      <section className="section-block">
        <div className="field">
          <label>تاريخ زيارة المراجعة</label>
          <input
            type="date"
            className="input"
            value={visitDate}
            onChange={(e) => {
              setVisitDate(e.target.value)
              scheduleInfoSave(e.target.value, visitorName)
            }}
          />
        </div>
        <div className="field">
          <label>اسم المراجع</label>
          <input
            type="text"
            className="input"
            value={visitorName}
            onChange={(e) => {
              setVisitorName(e.target.value)
              scheduleInfoSave(visitDate, e.target.value)
            }}
          />
        </div>
      </section>

      <section className="section-block review-summary">
        <h2>ملخص التجاوب</h2>
        <div className="progress-bar">
          <span style={{ width: `${rate}%` }} />
        </div>
        <div className="progress-label">{rate}٪ من الملاحظات ({resolved}/{total}) تمت معالجتها</div>
      </section>

      <section className="section-block">
        <h2>الصور — قبل / بعد</h2>
        {PHOTO_CATEGORIES.map((category) => (
          <ReviewPhotoUploader
            key={category}
            reviewId={review.id}
            reportId={review.report_id}
            category={category}
            label={PHOTO_CATEGORY_LABELS[category]}
            beforePhotos={review.report.photos.filter((p) => p.category === category)}
            afterPhotos={review.photos.filter((p) => p.category === category)}
            onChange={(photos) =>
              setReview((prev) =>
                prev
                  ? {
                      ...prev,
                      photos: [...prev.photos.filter((p) => p.category !== category), ...photos],
                    }
                  : prev,
              )
            }
          />
        ))}
      </section>

      <section className="section-block">
        <h2>الملاحظات</h2>
        {NOTE_CATEGORIES.map((category) => (
          <ReviewNoteSection
            key={category}
            label={NOTE_CATEGORY_LABELS[category]}
            notes={review.notes.filter((n) => n.category === category)}
            onUpdate={updateNote}
            onAdd={(item) => addNote(category, item)}
            onRemove={removeNote}
          />
        ))}
      </section>

      <div className="report-actions">
        <button
          type="button"
          className="btn-primary sticky-cta"
          disabled={downloading}
          onClick={downloadPptx}
        >
          {downloading ? 'جارٍ إصدار المراجعة...' : 'إصدار تقرير المراجعة (PPTX)'}
        </button>
        <button
          type="button"
          className="btn-secondary"
          disabled={downloadingPdf}
          onClick={downloadPdf}
        >
          {downloadingPdf ? 'جارٍ إصدار PDF...' : 'إصدار نسخة PDF'}
        </button>
      </div>
    </div>
  )
}

function ReviewNoteSection({
  label,
  notes,
  onUpdate,
  onAdd,
  onRemove,
}: {
  label: string
  notes: ReviewNote[]
  onUpdate: (note: ReviewNote, patch: Partial<ReviewNote>) => void
  onAdd: (item: string) => void
  onRemove: (noteId: number) => void
}) {
  const [newItem, setNewItem] = useState('')
  const noteTimers = useRef<Record<number, number>>({})

  function handleNoteTextChange(note: ReviewNote, text: string) {
    onUpdate(note, { note: text })
  }

  function debouncedNoteChange(note: ReviewNote, text: string) {
    // optimistic local update happens inside onUpdate already; just debounce
    // how often we actually hit the network while typing.
    window.clearTimeout(noteTimers.current[note.id])
    noteTimers.current[note.id] = window.setTimeout(() => handleNoteTextChange(note, text), 500)
  }

  return (
    <div className="checklist-section review-note-section">
      <div className="section-header">
        <h3>{label}</h3>
      </div>
      <div className="checklist-rows">
        {notes.map((note) => (
          <div className="review-note-row" key={note.id}>
            <div className="review-note-item">
              <span>{note.item}</span>
              {note.original_note_id == null && (
                <button
                  type="button"
                  className="link-button danger"
                  onClick={() => onRemove(note.id)}
                >
                  حذف
                </button>
              )}
            </div>
            <div className="checklist-row-fields">
              <input
                type="text"
                className="input note-input"
                placeholder="الإجراء المتخذ / الملاحظة الحالية"
                defaultValue={note.note}
                onChange={(e) => debouncedNoteChange(note, e.target.value)}
              />
              <select
                className="select status-select"
                value={note.response_status}
                onChange={(e) => onUpdate(note, { response_status: e.target.value })}
              >
                <option value="">مدى التجاوب...</option>
                {REVIEW_RESPONSE_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>
          </div>
        ))}
      </div>
      <div className="add-custom">
        <input
          type="text"
          className="input"
          placeholder="إضافة ملاحظة جديدة اكتُشفت أثناء المراجعة..."
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              onAdd(newItem)
              setNewItem('')
            }
          }}
        />
        <button
          type="button"
          className="btn-secondary"
          onClick={() => {
            onAdd(newItem)
            setNewItem('')
          }}
        >
          إضافة
        </button>
      </div>
    </div>
  )
}
