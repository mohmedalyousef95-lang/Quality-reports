import { useLocation, useNavigate } from 'react-router-dom'

export default function AppBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const isHome = location.pathname === '/'

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

      {!isHome ? (
        <button
          type="button"
          className="app-bar-btn"
          aria-label="الرئيسية"
          onClick={() => navigate('/')}
        >
          الرئيسية
        </button>
      ) : (
        <span className="app-bar-spacer" />
      )}
    </header>
  )
}
