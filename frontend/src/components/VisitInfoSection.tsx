import { useEffect, useRef, useState } from 'react'
import { api, type ReportInfo } from '../api'
import { showToast } from './Toast'

const TEAM_TYPE_OPTIONS = ['صيانة عامة', 'تكييف', 'أعمال مدنية', 'نظافة', 'أمن وسلامة']

type Props = {
  reportId: number
  initial: ReportInfo
}

export default function VisitInfoSection({ reportId, initial }: Props) {
  const [info, setInfo] = useState<ReportInfo>(initial)
  const [otherTeamType, setOtherTeamType] = useState('')
  const [saving, setSaving] = useState(false)
  const timer = useRef<number | undefined>(undefined)
  const initialized = useRef(false)

  const selectedTeamTypes = info.team_types
    ? info.team_types.split(',').map((t) => t.trim()).filter(Boolean)
    : []

  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true
      return
    }
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(save, 600)
    return () => window.clearTimeout(timer.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [info])

  async function save() {
    setSaving(true)
    try {
      await api.updateReportInfo(reportId, info)
    } catch {
      showToast('تعذّر حفظ معلومات الزيارة', 'error')
    } finally {
      setSaving(false)
    }
  }

  function set<K extends keyof ReportInfo>(key: K, value: ReportInfo[K]) {
    setInfo((prev) => ({ ...prev, [key]: value }))
  }

  function toggleTeamType(type: string) {
    const next = selectedTeamTypes.includes(type)
      ? selectedTeamTypes.filter((t) => t !== type)
      : [...selectedTeamTypes, type]
    set('team_types', next.join(', '))
  }

  function addOtherTeamType() {
    const text = otherTeamType.trim()
    if (!text || selectedTeamTypes.includes(text)) return
    set('team_types', [...selectedTeamTypes, text].join(', '))
    setOtherTeamType('')
  }

  return (
    <section className="section-block">
      <div className="section-header">
        <h2>معلومات الزيارة الإضافية</h2>
        {saving && <span className="saving-hint">جارٍ الحفظ...</span>}
      </div>

      <div className="field">
        <label>المقاول المسؤول</label>
        <input
          type="text"
          className="input"
          value={info.contractor}
          onChange={(e) => set('contractor', e.target.value)}
        />
      </div>

      <div className="field">
        <label>نوع الزيارة</label>
        <select
          className="select full-width"
          value={info.visit_type}
          onChange={(e) => set('visit_type', e.target.value)}
        >
          <option value="">— اختر —</option>
          <option value="تفقدية">زيارة تفقدية</option>
          <option value="خطة الاستعداد المدرسي">زيارة أثناء خطة الاستعداد المدرسي</option>
        </select>
      </div>

      <div className="field-row">
        <div className="field">
          <label>أثناء خطة الاستعداد المدرسي؟</label>
          <select
            className="select full-width"
            value={info.during_readiness_plan}
            onChange={(e) => set('during_readiness_plan', e.target.value)}
          >
            <option value="">—</option>
            <option value="نعم">نعم</option>
            <option value="لا">لا</option>
          </select>
        </div>
        <div className="field">
          <label>مشرف مكتب العمران متواجد؟</label>
          <select
            className="select full-width"
            value={info.oversight_supervisor_present}
            onChange={(e) => set('oversight_supervisor_present', e.target.value)}
          >
            <option value="">—</option>
            <option value="نعم">نعم</option>
            <option value="لا">لا</option>
          </select>
        </div>
      </div>

      <div className="field">
        <label>عدد الفرق الموجودة أثناء الزيارة</label>
        <input
          type="number"
          min={0}
          className="input"
          value={info.team_count ?? ''}
          onChange={(e) => set('team_count', e.target.value === '' ? null : Number(e.target.value))}
        />
      </div>

      <div className="field">
        <label>نوع الفرق الموجودة</label>
        <div className="chip-row">
          {TEAM_TYPE_OPTIONS.map((type) => (
            <label key={type} className={`chip ${selectedTeamTypes.includes(type) ? 'chip-active' : ''}`}>
              <input
                type="checkbox"
                checked={selectedTeamTypes.includes(type)}
                onChange={() => toggleTeamType(type)}
              />
              {type}
            </label>
          ))}
          {selectedTeamTypes
            .filter((t) => !TEAM_TYPE_OPTIONS.includes(t))
            .map((type) => (
              <label key={type} className="chip chip-active">
                <input type="checkbox" checked onChange={() => toggleTeamType(type)} />
                {type}
              </label>
            ))}
        </div>
        <div className="add-custom">
          <input
            type="text"
            className="input"
            placeholder="نوع فريق آخر..."
            value={otherTeamType}
            onChange={(e) => setOtherTeamType(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                addOtherTeamType()
              }
            }}
          />
          <button type="button" className="btn-secondary" onClick={addOtherTeamType}>
            إضافة
          </button>
        </div>
      </div>

      <div className="field">
        <label>الملاحظات المهمة (اختياري)</label>
        <textarea
          className="input textarea"
          rows={3}
          value={info.important_notes}
          onChange={(e) => set('important_notes', e.target.value)}
          placeholder="أي ملاحظات مهمة تُضاف إلى شريحة معلومات المدرسة..."
        />
      </div>
    </section>
  )
}
