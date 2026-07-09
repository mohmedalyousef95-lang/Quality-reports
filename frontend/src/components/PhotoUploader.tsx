import { useEffect, useRef, useState } from 'react'
import { api, type ReportPhoto } from '../api'
import { MAX_PHOTOS_PER_CATEGORY } from '../constants'
import { showToast } from './Toast'

type Props = {
  reportId: number
  category: string
  label: string
  photos: ReportPhoto[]
  onChange: (photos: ReportPhoto[]) => void
}

export default function PhotoUploader({ reportId, category, label, photos, onChange }: Props) {
  const [uploading, setUploading] = useState(false)
  const [preview, setPreview] = useState<string | null>(null)
  const cameraRef = useRef<HTMLInputElement>(null)
  const galleryRef = useRef<HTMLInputElement>(null)
  const sectionRef = useRef<HTMLDivElement>(null)

  const remaining = MAX_PHOTOS_PER_CATEGORY - photos.length

  async function uploadMany(files: File[]) {
    if (files.length === 0) return
    setUploading(true)
    try {
      const toUpload = files.slice(0, remaining)
      const uploaded: ReportPhoto[] = []
      for (const file of toUpload) {
        const result = await api.uploadPhoto(reportId, category, file)
        uploaded.push(result)
      }
      onChange([...photos, ...uploaded])
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

  // Paste multiple images at once (clipboard button + Ctrl/Cmd+V on the section)
  async function pasteFromClipboard() {
    try {
      if (!navigator.clipboard || !navigator.clipboard.read) {
        showToast('اللصق غير مدعوم في هذا المتصفح — استخدم الاستوديو', 'error')
        return
      }
      const items = await navigator.clipboard.read()
      const files: File[] = []
      for (const item of items) {
        const type = item.types.find((t) => t.startsWith('image/'))
        if (type) {
          const blob = await item.getType(type)
          const ext = type.split('/')[1] || 'png'
          files.push(new File([blob], `pasted-${Date.now()}-${files.length}.${ext}`, { type }))
        }
      }
      if (files.length === 0) {
        showToast('لا توجد صور في الحافظة', 'info')
        return
      }
      await uploadMany(files)
    } catch {
      showToast('تعذّر قراءة الحافظة — امنح الإذن أو استخدم Ctrl+V', 'error')
    }
  }

  useEffect(() => {
    const el = sectionRef.current
    if (!el) return
    function onPaste(e: ClipboardEvent) {
      const items = e.clipboardData?.items
      if (!items) return
      const files: File[] = []
      for (const it of items) {
        if (it.type.startsWith('image/')) {
          const f = it.getAsFile()
          if (f) files.push(f)
        }
      }
      if (files.length > 0) {
        e.preventDefault()
        uploadMany(files)
      }
    }
    el.addEventListener('paste', onPaste as EventListener)
    return () => el.removeEventListener('paste', onPaste as EventListener)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [photos, remaining])

  async function handleDelete(photoId: number) {
    await api.deletePhoto(reportId, photoId)
    onChange(photos.filter((p) => p.id !== photoId))
  }

  const captionTimers = useRef<Record<number, number>>({})
  function handleCaption(photoId: number, value: string) {
    onChange(photos.map((p) => (p.id === photoId ? { ...p, caption: value } : p)))
    window.clearTimeout(captionTimers.current[photoId])
    captionTimers.current[photoId] = window.setTimeout(() => {
      api.updateCaption(reportId, photoId, value).catch(() => {})
    }, 500)
  }

  return (
    <div className="photo-section" ref={sectionRef} tabIndex={-1}>
      <div className="section-header">
        <h3>{label}</h3>
        <span className="count-badge">
          {photos.length}/{MAX_PHOTOS_PER_CATEGORY}
        </span>
      </div>

      <div className="photo-grid">
        {photos.map((photo) => {
          const url = `/api/reports/${reportId}/photos/${photo.id}/file`
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
              <input
                type="text"
                className="photo-caption-input"
                placeholder="تعليق (اختياري)"
                value={photo.caption ?? ''}
                onChange={(e) => handleCaption(photo.id, e.target.value)}
              />
            </div>
          )
        })}
      </div>

      {remaining > 0 && (
        <div className="photo-actions">
          {/* Camera is the primary action */}
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
          <button
            type="button"
            className="photo-btn"
            disabled={uploading}
            onClick={pasteFromClipboard}
          >
            📋 لصق صور
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
