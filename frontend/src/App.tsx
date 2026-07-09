import { useEffect, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { api } from './api'
import Login from './pages/Login'
import Home from './pages/Home'
import ReportEditor from './pages/ReportEditor'
import SchoolHistory from './pages/SchoolHistory'
import IosInstallHint from './components/IosInstallHint'

export default function App() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null)

  useEffect(() => {
    api
      .authStatus()
      .then((s) => setAuthenticated(s.authenticated))
      .catch(() => setAuthenticated(false))
  }, [])

  if (authenticated === null) {
    return <div className="centered-page">جارٍ التحميل...</div>
  }

  if (!authenticated) {
    return (
      <Routes>
        <Route path="*" element={<Login onLoggedIn={() => setAuthenticated(true)} />} />
      </Routes>
    )
  }

  return (
    <>
      <IosInstallHint />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/reports/:id" element={<ReportEditor />} />
        <Route path="/schools/:id" element={<SchoolHistory />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}
