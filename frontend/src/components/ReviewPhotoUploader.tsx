import { useRef, useState } from 'react'
import { api, type ReviewPhoto, type ReportPhoto } from '../api'
import { MAX_PHOTOS_PER_CATEGORY } from '../constants'
import { showToast } from './Toast'

type Props = {
  reviewId: number
  reportId: number
  category: string
  label: string
  beforePhotos: ReportPhoto[]
  afterPhotos: ReviewPhoto[]
  onChange: (photos: ReviewPhoto[]) => void
}

export default function ReviewPhotoUploader({
  reviewId,
  reportId,
  category,
  label,
  beforePhotos,
  afterPhotos,
  onChange,
}: Props) {
  const [uploading, setUploading] = useState(false)
  const [preview, setPreview] = useState<string | null>(null)
  const cameraRef = useRef<HTMLInputElement>(null)
  const galleryRef = useRef<HTMLInputElement>(null)

  const remaining = MAX_PHOTOS_PER_CATEGORY - afterPhotos.length

  async function uploadMany(files: File[]) {
    if (files.length === 0) return
    setUploading(true)
    try {
      const toUpload = files.slice(0, remaining)
      const uploaded: ReviewPhoto[] = []
      for (const file of toUpload) {
        const result = await api.uploadReviewPhoto(reviewId, category, file)
        uploaded.push(result)
      }
      onChange([...afterPhotos, ...uploaded])
      if (uploaded.length > 0) showToast(`تم رفع ${uploaded.length} صورة`, 'success')
    } catch {
      showToast('تعذّر رفع بعض الصور، حاول مرة أخرى', 'error')
    } finally {
      setUploading(false)
      if (cameraRef.current) cameraRef.current.value = ''
      if (galleryRef.current) galleryRef.current.value = ''
    }
  }

  function handleInput(files: FileList | null) {
    if (files) uploadMany(Array.from(files))
  }

  async function handleDelete(photoId: number) {
    await api.deleteReviewPhoto(reviewId, photoId)
    onChange(afterPhotos.filter((p) => p.id !== photoId))
  }

  if (beforePhotos.length === 0 && afterPhotos.length === 0 && remaining <= 0) return null

  return (
    <div className="photo-section review-photo-section">
      <div className="section-header">
        <h3>{label}</h3>
      </div>

      <div className="review-photo-compare">
        <div className="review-photo-col">
          <div className="review-photo-col-label">قبل</div>
          <div className="photo-grid">
            {beforePhotos.length === 0 && <div className="empty-hint small">لا توجد صور سابقة</div>}
            {beforePhotos.map((photo) => {
              const url = `/api/reports/${reportId}/photos/${photo.id}/file`
              return (
                <div className="photo-item" key={photo.id}>
                  <div className="photo-thumb">
                    <img src={url} alt="" onClick={() => setPreview(url)} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <div className="review-photo-col">
          <div className="review-photo-col-label">بعد</div>
          <div className="photo-grid">
            {afterPhotos.map((photo) => {
              const url = `/api/reviews/${reviewId}/photos/${photo.id}/file`
              return (
                <div className="photo-item" key={photo.id}>
                  <div className="photo-thumb">
                    <img src={url} alt="" onClick={() => setPreview(url)} />
                    <button
                      type="button"
                      className="photo-remove"
                      onClick={() => handleDelete(photo.id)}
                      aria-label="حذف الصورة"
                    >
                      ×
                    </button>
                  </div>
                </div>
              )
            })}
          </div>

          {remaining > 0 && (
            <div className="photo-actions">
              <button
                type="button"
                className="photo-btn photo-btn-primary"
                disabled={uploading}
                onClick={() => cameraRef.current?.click()}
              >
                📷 التقاط صورة
              </button>
              <button
                type="button"
                className="photo-btn"
                disabled={uploading}
                onClick={() => galleryRef.current?.click()}
              >
                🖼️ من الاستوديو
              </button>
              <input
                ref={cameraRef}
                type="file"
                accept="image/*"
                capture="environment"
                hidden
                onChange={(e) => handleInput(e.target.files)}
              />
              <input
                ref={galleryRef}
                type="file"
                accept="image/*"
                multiple
                hidden
                onChange={(e) => handleInput(e.target.files)}
              />
            </div>
          )}
          {uploading && <div className="upload-hint">جارٍ رفع الصور...</div>}
        </div>
      </div>

      {preview && (
        <div className="lightbox" onClick={() => setPreview(null)}>
          <img src={preview} alt="" />
          <button type="button" className="lightbox-close" aria-label="إغلاق">
            ×
          </button>
        </div>
      )}
    </div>
  )
}
