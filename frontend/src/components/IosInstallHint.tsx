import { useEffect, useState } from 'react'

const DISMISS_KEY = 'iosInstallHintDismissed'

function isIos(): boolean {
  const ua = window.navigator.userAgent
  const iOS = /iPad|iPhone|iPod/.test(ua)
  // iPadOS 13+ reports as Mac; detect touch + Mac
  const iPadOS = navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1
  return iOS || iPadOS
}

function isStandalone(): boolean {
  // @ts-expect-error - iOS Safari specific
  return window.navigator.standalone === true ||
    window.matchMedia('(display-mode: standalone)').matches
}

export default function IosInstallHint() {
  const [show, setShow] = useState(false)

  useEffect(() => {
    if (isIos() && !isStandalone() && !localStorage.getItem(DISMISS_KEY)) {
      setShow(true)
    }
  }, [])

  if (!show) return null

  return (
    <div className="ios-hint">
      <div className="ios-hint-text">
        لتثبيت التطبيق على جهازك: اضغط
        <span className="ios-hint-icon" aria-hidden="true"> ⬆️ </span>
        (مشاركة) ثم «إضافة إلى الشاشة الرئيسية»
      </div>
      <button
        type="button"
        className="ios-hint-close"
        aria-label="إغلاق"
        onClick={() => {
          localStorage.setItem(DISMISS_KEY, '1')
          setShow(false)
        }}
      >
        ×
      </button>
    </div>
  )
}
