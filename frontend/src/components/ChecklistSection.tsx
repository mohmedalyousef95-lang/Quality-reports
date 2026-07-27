import { useEffect, useRef, useState } from 'react'
import { api, type ChecklistItem, type NoteSuggestion, type ReportNote } from '../api'

const STATUS_OPTIONS = ['نعم', 'لا', 'جاري العمل عليها']

type Row = {
  key: string
  item: string
  checked: boolean
  note: string
  status: string
}

type Props = {
  reportId: number
  category: string
  label: string
  initialNotes: ReportNote[]
}

export default function ChecklistSection({ reportId, category, label, initialNotes }: Props) {
  const [checklist, setChecklist] = useState<ChecklistItem[]>([])
  const [suggestions, setSuggestions] = useState<NoteSuggestion[]>([])
  const [rows, setRows] = useState<Row[]>([])
  const [customText, setCustomText] = useState('')
  const [saveToChecklist, setSaveToChecklist] = useState(true)
  const [saving, setSaving] = useState(false)
  const saveTimer = useRef<number | undefined>(undefined)
  const initialized = useRef(false)

  useEffect(() => {
    api.getNoteSuggestions().then(setSuggestions).catch(() => {})
  }, [])

  function suggestionsFor(item: string) {
    return suggestions.filter((s) => s.category === category && s.item === item)
  }

  useEffect(() => {
    api.getChecklist(category).then((items) => {
      setChecklist(items)
      const noteByItem = new Map(initialNotes.map((n) => [n.item, n]))
      const built: Row[] = items.map((ci) => {
        const existing = noteByItem.get(ci.label)
        return {
          key: ci.label,
          item: ci.label,
          checked: noteByItem.has(ci.label),
          note: existing?.note ?? '',
          status: existing?.status ?? '',
        }
      })
      for (const n of initialNotes) {
        if (!items.some((ci) => ci.label === n.item)) {
          built.push({ key: n.item, item: n.item, checked: true, note: n.note, status: n.status ?? '' })
        }
      }
      setRows(built)
      initialized.current = true
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category])

  useEffect(() => {
    if (!initialized.current) return
    window.clearTimeout(saveTimer.current)
    saveTimer.current = window.setTimeout(() => {
      persist()
    }, 500)
    return () => window.clearTimeout(saveTimer.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows])

  async function persist() {
    setSaving(true)
    try {
      const checkedRows = rows.filter((r) => r.checked)
      await api.replaceNotes(
        reportId,
        category,
        checkedRows.map((r, i) => ({ category, item: r.item, note: r.note, status: r.status, position: i })),
      )
    } finally {
      setSaving(false)
    }
  }

  function toggle(key: string) {
    setRows((prev) => prev.map((r) => (r.key === key ? { ...r, checked: !r.checked } : r)))
  }

  function updateNote(key: string, note: string) {
    setRows((prev) => prev.map((r) => (r.key === key ? { ...r, note } : r)))
  }

  function updateStatus(key: string, status: string) {
    setRows((prev) => prev.map((r) => (r.key === key ? { ...r, status } : r)))
  }

  async function addCustom() {
    const text = customText.trim()
    if (!text) return
    setRows((prev) => [...prev, { key: text, item: text, checked: true, note: '', status: '' }])
    setCustomText('')
    if (saveToChecklist && !checklist.some((ci) => ci.label === text)) {
      try {
        const created = await api.addChecklistItem(category, text)
        setChecklist((prev) => [...prev, created])
      } catch {
        // duplicate or failure - ignore, item still added to this report
      }
    }
  }

  return (
    <div className="checklist-section">
      <div className="section-header">
        <h3>{label}</h3>
        {saving && <span className="saving-hint">جارٍ الحفظ...</span>}
      </div>
      <div className="checklist-rows">
        {rows.map((row) => (
          <div className={`checklist-row ${row.checked ? 'checked' : ''}`} key={row.key}>
            <label className="checklist-toggle">
              <input type="checkbox" checked={row.checked} onChange={() => toggle(row.key)} />
              <span>{row.item}</span>
            </label>
            {row.checked && (
              <div className="checklist-row-fields">
                {suggestionsFor(row.item).length > 0 && (
                  <select
                    className="select suggestion-select"
                    value=""
                    onChange={(e) => {
                      if (e.target.value) updateNote(row.key, e.target.value)
                    }}
                  >
                    <option value="">ملاحظات جاهزة...</option>
                    {suggestionsFor(row.item).map((s) => (
                      <option key={s.id} value={s.text}>
                        {s.text}
                      </option>
                    ))}
                  </select>
                )}
                <input
                  type="text"
                  className="input note-input"
                  placeholder="إجراءات المعالجة (اختياري)"
                  value={row.note}
                  onChange={(e) => updateNote(row.key, e.target.value)}
                />
                <select
                  className="select status-select"
                  value={row.status}
                  onChange={(e) => updateStatus(row.key, e.target.value)}
                >
                  <option value="">هل تمت المعالجة؟</option>
                  {STATUS_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="add-custom">
        <input
          type="text"
          className="input"
          placeholder="إضافة بند آخر..."
          value={customText}
          onChange={(e) => setCustomText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              addCustom()
            }
          }}
        />
        <button type="button" className="btn-secondary" onClick={addCustom}>
          إضافة
        </button>
      </div>
      <label className="save-to-checklist">
        <input
          type="checkbox"
          checked={saveToChecklist}
          onChange={(e) => setSaveToChecklist(e.target.checked)}
        />
        <span>احفظ البنود الجديدة في القائمة الجاهزة للاستخدام لاحقاً</span>
      </label>
    </div>
  )
}
