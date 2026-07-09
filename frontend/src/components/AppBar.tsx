import { useLocation, useNavigate } from 'react-router-dom'

export default function AppBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const isHome = location.pathname === '/'
  const isReports = location.pathname === '/reports'

  return (
    <header className="app-bar">
      {!isHome ? (
        <button
          type="button"
          className="app-bar-btn"
          aria-label="رجوع"
          onClick={() => navigate(-1)}
        >
          ‹ رجوع
        </button>
      ) : (
        <span className="app-bar-spacer" />
      )}

      <div className="app-bar-title" onClick={() => navigate('/')}>
        تقارير الجودة
      </div>

      {isReports ? (
        <button type="button" className="app-bar-btn" onClick={() => navigate('/')}>
          + تقرير
        </button>
      ) : (
        <button type="button" className="app-bar-btn" onClick={() => navigate('/reports')}>
          التقارير
        </button>
      )}
    </header>
  )
}
