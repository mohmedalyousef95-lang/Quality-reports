import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import SchoolAutocomplete from '../components/SchoolAutocomplete'
import { api, type School } from '../api'

const VISITOR_NAME_KEY = 'lastVisitorName'

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

export default function Home() {
  const [school, setSchool] = useState<School | null>(null)
  const [visitDate, setVisitDate] = useState(today())
  const [visitorName, setVisitorName] = useState(
    localStorage.getItem(VISITOR_NAME_KEY) || '',
  )
  const [creating, setCreating] = useState(false)
  const navigate = useNavigate()

  async function startReport() {
    if (!school) return
    setCreating(true)
    try {
      localStorage.setItem(VISITOR_NAME_KEY, visitorName)
      const report = await api.createReport({
        school_id: school.ministry_number,
        visit_date: visitDate,
        visitor_name: visitorName,
      })
      navigate(`/reports/${report.id}`)
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="page">
      <div className="home-head">
        <h1 className="page-title">تقرير جديد</h1>
        <button type="button" className="btn-secondary" onClick={() => navigate('/reports')}>
          📋 كل التقارير
        </button>
      </div>

      <div className="field">
        <label>المدرسة</label>
        <SchoolAutocomplete onSelect={setSchool} />
      </div>

      {school && (
        <div className="school-card">
          <div className="school-card-name">{school.name}</div>
          <div className="school-card-row">
            <span>المنطقة</span>
            <span>{school.region}</span>
          </div>
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
            <span>الرقم الوزاري</span>
            <span>{school.ministry_number}</span>
          </div>
          <button
            type="button"
            className="link-button"
            onClick={() => navigate(`/schools/${school.ministry_number}`)}
          >
            عرض سجل الزيارات السابقة
          </button>
        </div>
      )}

      <div className="field">
        <label>تاريخ الزيارة</label>
        <input
          type="date"
          className="input"
          value={visitDate}
          onChange={(e) => setVisitDate(e.target.value)}
        />
      </div>

      <div className="field">
        <label>اسم الزائر</label>
        <input
          type="text"
          className="input"
          value={visitorName}
          onChange={(e) => setVisitorName(e.target.value)}
        />
      </div>

      <button
        type="button"
        className="btn-primary sticky-cta"
        disabled={!school || !visitorName || creating}
        onClick={startReport}
      >
        {creating ? 'جارٍ الإنشاء...' : 'بدء التقرير'}
      </button>
    </div>
  )
}
