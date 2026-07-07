import { useRef, useState } from 'react'
import { api, type ReportPhoto } from '../api'
import { MAX_PHOTOS_PER_CATEGORY } from '../constants'

type Props = {
  reportId: number
  category: string
  label: string
  photos: ReportPhoto[]
  onChange: (photos: ReportPhoto[]) => void
}

export default function PhotoUploader({ reportId, category, label, photos, onChange }: Props) {
  const [uploading, setUploading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const remaining = MAX_PHOTOS_PER_CATEGORY - photos.length

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return
    setUploading(true)
    try {
      const toUpload = Array.from(files).slice(0, remaining)
      const uploaded: ReportPhoto[] = []
      for (const file of toUpload) {
        const result = await api.uploadPhoto(reportId, category, file)
        uploaded.push(result)
      }
      onChange([...photos, ...uploaded])
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  async function handleDelete(photoId: number) {
    await api.deletePhoto(reportId, photoId)
    onChange(photos.filter((p) => p.id !== photoId))
  }

  return (
    <div className="photo-section">
      <div className="section-header">
        <h3>{label}</h3>
        <span className="count-badge">
          {photos.length}/{MAX_PHOTOS_PER_CATEGORY}
        </span>
      </div>
      <div className="photo-grid">
        {photos.map((photo) => (
          <div className="photo-thumb" key={photo.id}>
            <img src={`/api/reports/${reportId}/photos/${photo.id}/file`} alt="" />
            <button
              type="button"
              className="photo-remove"
              onClick={() => handleDelete(photo.id)}
              aria-label="حذف الصورة"
            >
              ×
            </button>
          </div>
        ))}
        {remaining > 0 && (
          <label className="photo-add">
            {uploading ? '...' : '+ إضافة'}
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              capture="environment"
              multiple
              hidden
              disabled={uploading}
              onChange={(e) => handleFiles(e.target.files)}
            />
          </label>
        )}
      </div>
    </div>
  )
}
