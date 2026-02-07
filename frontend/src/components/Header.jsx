import { Link } from 'react-router-dom'

function Header() {
  return (
    <header className="bg-red-600 text-white shadow-lg">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold">BrickGen</h1>
            <span className="text-sm opacity-90">LEGO 3D Printer Generator</span>
          </Link>
          <nav>
            <Link
              to="/settings"
              className="px-4 py-2 bg-red-700 hover:bg-red-800 rounded transition"
            >
              Settings
            </Link>
          </nav>
        </div>
      </div>
    </header>
  )
}

export default Header
