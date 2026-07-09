import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type ReportRow, type FilterOptions } from '../api'
import { showToast } from '../components/Toast'

const STATUS_LABEL: Record<string, string> = {
  draft: 'غير مكتمل',
  completed: 'مكتمل',
}

export default function ReportsList() {
  const navigate = useNavigate()
  const [rows, setRows] = useState<ReportRow[]>([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState<FilterOptions>({ zones: [], engineers: [], supervisors: [] })

  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [zone, setZone] = useState('')
  const [engineer, setEngineer] = useState('')
  const [supervisor, setSupervisor] = useState('')
  const [sort, setSort] = useState('recent')
  const timer = useRef<number | undefined>(undefined)

  useEffect(() => {
    api.getReportFilters().then(setFilters).catch(() => {})
  }, [])

  useEffect(() => {
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(load, 250)
    return () => window.clearTimeout(timer.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, status, zone, engineer, supervisor, sort])

  async function load() {
    setLoading(true)
    try {
      const data = await api.listReports({ search, status, zone, engineer, supervisor, sort })
      setRows(data)
    } finally {
      setLoading(false)
    }
  }

  async function remove(id: number) {
    if (!confirm('حذف هذا التقرير نهائياً؟')) return
    await api.deleteReport(id)
    setRows((prev) => prev.filter((r) => r.id !== id))
    showToast('تم حذف التقرير', 'success')
  }

  function reset() {
    setSearch(''); setStatus(''); setZone(''); setEngineer(''); setSupervisor(''); setSort('recent')
  }

  const activeFilters = [status, zone, engineer, supervisor].filter(Boolean).length

  return (
    <div className="page">
      <h1 className="page-title">التقارير</h1>

      <input
        type="text"
        className="input"
        placeholder="ابحث باسم المدرسة أو الرقم الوزاري"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      <div className="filters-row">
        <select className="select" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">كل الحالات</option>
          <option value="completed">مكتمل</option>
          <option value="draft">غير مكتمل</option>
        </select>
        <select className="select" value={zone} onChange={(e) => setZone(e.target.value)}>
          <option value="">كل الزون</option>
          {filters.zones.map((z) => <option key={z} value={z}>{z}</option>)}
        </select>
        <select className="select" value={engineer} onChange={(e) => setEngineer(e.target.value)}>
          <option value="">كل المهندسين</option>
          {filters.engineers.map((z) => <option key={z} value={z}>{z}</option>)}
        </select>
        <select className="select" value={supervisor} onChange={(e) => setSupervisor(e.target.value)}>
          <option value="">كل المشرفين</option>
          {filters.supervisors.map((z) => <option key={z} value={z}>{z}</option>)}
        </select>
        <select className="select" value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="recent">الأحدث أولاً</option>
          <option value="oldest">الأقدم أولاً</option>
          <option value="school">اسم المدرسة</option>
        </select>
        {(activeFilters > 0 || search) && (
          <button type="button" className="btn-secondary" onClick={reset}>مسح الفلاتر</button>
        )}
      </div>

      <div className="results-count">
        {loading ? 'جارٍ التحميل...' : `${rows.length} تقرير`}
      </div>

      <ul className="report-list">
        {rows.map((r) => (
          <li key={r.id} className="report-card" onClick={() => navigate(`/reports/${r.id}`)}>
            <div className="report-card-main">
              <div className="report-card-name">{r.school_name}</div>
              <div className="report-card-meta">
                {r.visit_date} · {r.zone} · {r.visitor_name || '—'}
              </div>
              <div className="report-card-progress">
                <div className="progress-bar">
                  <span style={{ width: `${r.completion}%` }} />
                </div>
                <span className="progress-label">{r.completion}%</span>
              </div>
            </div>
            <div className="report-card-side" onClick={(e) => e.stopPropagation()}>
              <span className={`status-badge status-${r.status}`}>{STATUS_LABEL[r.status]}</span>
              <div className="report-card-actions">
                <button
                  type="button"
                  className="link-button"
                  onClick={() => api.downloadReport(r.id, `${r.school_name}_${r.visit_date}.pptx`)}
                >
                  تنزيل
                </button>
                <button type="button" className="link-button danger" onClick={() => remove(r.id)}>
                  حذف
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>

      {!loading && rows.length === 0 && (
        <div className="empty-hint">لا توجد تقارير مطابقة</div>
      )}
    </div>
  )
}
