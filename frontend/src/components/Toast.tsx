import { useEffect, useState } from 'react'

type ToastType = 'info' | 'success' | 'error'
type ToastItem = { id: number; message: string; type: ToastType }

type Listener = (t: ToastItem) => void
let listeners: Listener[] = []
let counter = 0

export function showToast(message: string, type: ToastType = 'info') {
  const item = { id: ++counter, message, type }
  listeners.forEach((l) => l(item))
}

export default function ToastHost() {
  const [items, setItems] = useState<ToastItem[]>([])

  useEffect(() => {
    const listener: Listener = (t) => {
      setItems((prev) => [...prev, t])
      setTimeout(() => {
        setItems((prev) => prev.filter((x) => x.id !== t.id))
      }, 3500)
    }
    listeners.push(listener)
    return () => {
      listeners = listeners.filter((l) => l !== listener)
    }
  }, [])

  if (items.length === 0) return null

  return (
    <div className="toast-host">
      {items.map((t) => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          {t.message}
        </div>
      ))}
    </div>
  )
}
