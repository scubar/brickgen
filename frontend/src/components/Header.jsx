import { Link } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { apiFetch } from '../api'

function Header() {
  const [ldrawExists, setLdrawExists] = useState(true)
  const [checkingLdraw, setCheckingLdraw] = useState(true)

  useEffect(() => {
    const checkLdrawStatus = async () => {
      try {
        const r = await apiFetch('/api/ldraw/stats')
        if (r.ok) {
          const data = await r.json()
          setLdrawExists(data.exists)
        }
      } catch (e) {
        console.error('Failed to check LDraw status:', e)
      } finally {
        setCheckingLdraw(false)
      }
    }
    checkLdrawStatus()
  }, [])

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
            <Link 
              to="/settings" 
              className="px-4 py-2 bg-dk-3 text-dk-5 hover:bg-mint hover:text-dk-1 rounded transition relative group"
              title={!checkingLdraw && !ldrawExists ? "LDraw library not downloaded - click Settings to download it from the Cache tab" : undefined}
            >
              Settings
              {!checkingLdraw && !ldrawExists && (
                <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-amber-500 text-dk-1 text-xs font-bold">
                  !
                </span>
              )}
            </Link>
            <Link to="/attributions" className="px-4 py-2 bg-dk-3 text-dk-5 hover:bg-mint hover:text-dk-1 rounded transition">
              Attributions
            </Link>
          </nav>
        </div>
      </div>
    </header>
  )
}

export default Header
