import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

function Header() {
  const { isAuthenticated, logout, user } = useAuth()
  const location = useLocation()

  // Don't show header on login page
  if (location.pathname === '/login') {
    return null
  }

  return (
    <header className="bg-dk-2 border-b border-dk-3 shadow-lg">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-2 text-dk-5 hover:text-mint transition">
            <h1 className="text-2xl font-bold">BrickGen</h1>
          </Link>
          <nav className="flex items-center gap-2">
            <Link to="/projects" className="px-4 py-2 bg-dk-3 text-dk-5 hover:bg-mint hover:text-dk-1 rounded transition">
              Projects
            </Link>
            <Link to="/guide" className="px-4 py-2 bg-dk-3 text-dk-5 hover:bg-mint hover:text-dk-1 rounded transition">
              Guide
            </Link>
            <Link to="/settings" className="px-4 py-2 bg-dk-3 text-dk-5 hover:bg-mint hover:text-dk-1 rounded transition">
              Settings
            </Link>
            <Link to="/attributions" className="px-4 py-2 bg-dk-3 text-dk-5 hover:bg-mint hover:text-dk-1 rounded transition">
              Attributions
            </Link>
            {isAuthenticated && (
              <>
                <span className="px-3 py-2 text-dk-5 text-sm">
                  {user}
                </span>
                <button
                  onClick={logout}
                  className="px-4 py-2 bg-red-600 text-white hover:bg-red-700 rounded transition"
                >
                  Logout
                </button>
              </>
            )}
          </nav>
        </div>
      </div>
    </header>
  )
}

export default Header
