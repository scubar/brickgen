import { Link } from 'react-router-dom'

function Header() {
  return (
    <header className="bg-grey-400 text-white shadow-lg">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold">BrickGen</h1>
          </Link>
          <nav className="flex items-center gap-2">
            <Link to="/projects" className="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded transition">
              Projects
            </Link>
            <Link to="/settings" className="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded transition">
              Settings
            </Link>
            <Link to="/attributions" className="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded transition">
              Attributions
            </Link>
          </nav>
        </div>
      </div>
    </header>
  )
}

export default Header
