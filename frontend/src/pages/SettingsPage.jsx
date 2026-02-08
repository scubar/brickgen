import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import CacheManagementContent from '../components/CacheManagementContent'

function SettingsPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [activeTab, setActiveTab] = useState(() => (typeof window !== 'undefined' && window.location.pathname === '/settings/cache' ? 'cache' : 'general'))
  const [settings, setSettings] = useState({
    default_plate_width: 220,
    default_plate_depth: 220,
    default_plate_height: 250,
    part_spacing: 2,
    stl_scale_factor: 10,
    rotation_enabled: false,
    rotation_x: 0,
    rotation_y: 0,
    rotation_z: 0,
    default_orientation_match_preview: true,
    auto_generate_part_previews: true,
  })
  const [apiKey, setApiKey] = useState('')
  const [envPaths, setEnvPaths] = useState({
    ldraw_library_path: '/app/data/ldraw',
    cache_dir: '/app/cache',
    database_path: '/app/database/brickgen.db'
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [savingApiKey, setSavingApiKey] = useState(false)
  const [message, setMessage] = useState(null)
  useEffect(() => {
    fetchSettings()
  }, [])
  useEffect(() => {
    if (location.pathname === '/settings/cache') setActiveTab('cache')
  }, [location.pathname])

  const fetchSettings = async () => {
    try {
      const response = await fetch('/api/settings')
      if (response.ok) {
        const data = await response.json()
        setSettings(data)
      }
    } catch (err) {
      console.error('Failed to fetch settings:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveSettings = async (e) => {
    e.preventDefault()
    
    // Check if scale factor is being changed
    const currentScale = settings.stl_scale_factor
    const previousScale = (await fetch('/api/settings').then(r => r.json())).stl_scale_factor
    const scaleChanged = currentScale !== previousScale
    
    if (scaleChanged) {
      if (!confirm('⚠️ WARNING: Changing the scale factor will automatically clear all cached STL files. Are you sure?')) {
        return
      }
    }
    
    setSaving(true)
    setMessage(null)

    try {
      const response = await fetch('/api/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings),
      })

      if (response.ok) {
        const data = await response.json()
        if (data.cache_cleared) {
          setMessage({ type: 'success', text: 'Settings saved! STL cache was cleared due to scale or rotation change.' })
        } else {
          setMessage({ type: 'success', text: 'Settings saved successfully!' })
        }
      } else {
        throw new Error('Failed to save settings')
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setSaving(false)
    }
  }

  const handleSaveApiKey = async (e) => {
    e.preventDefault()
    
    if (!apiKey.trim()) {
      setMessage({ type: 'error', text: 'API key cannot be empty' })
      return
    }

    setSavingApiKey(true)
    setMessage(null)

    try {
      const response = await fetch('/api/settings/api-key', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ api_key: apiKey }),
      })

      if (response.ok) {
        setMessage({ type: 'success', text: 'API key updated successfully!' })
        setApiKey('')
      } else {
        throw new Error('Failed to update API key')
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setSavingApiKey(false)
    }
  }

  const clampRotation = (v) => {
    const n = parseFloat(v)
    if (Number.isNaN(n)) return 0
    return Math.max(-360, Math.min(360, n))
  }
  const handleChange = (field, value) => {
    if (['stl_scale_factor', 'rotation_x', 'rotation_y', 'rotation_z'].includes(field)) {
      const val = field.startsWith('rotation_') ? clampRotation(value) : (parseFloat(value) || 0)
      setSettings(prev => ({ ...prev, [field]: val }))
    } else if (field === 'rotation_enabled' || field === 'auto_generate_part_previews' || field === 'default_orientation_match_preview') {
      setSettings(prev => ({ ...prev, [field]: value }))
    } else {
      setSettings(prev => ({ ...prev, [field]: parseInt(value) }))
    }
  }

  if (loading) {
    return <div className="text-center py-8">Loading...</div>
  }

  const tabs = [
    { id: 'general', label: 'General' },
    { id: 'build', label: 'Build & rotation' },
    { id: 'cache', label: 'Cache' },
  ]

  const selectTab = (id) => {
    setActiveTab(id)
    setMessage(null)
    if (id === 'cache') navigate('/settings/cache')
    else navigate('/settings')
  }

  return (
    <div className="max-w-4xl mx-auto">
      <button
        onClick={() => navigate('/')}
        className="mb-4 px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
      >
        ← Back to Search
      </button>

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => selectTab(tab.id)}
                className={`flex-1 py-4 px-6 text-center border-b-2 font-medium text-sm transition ${
                  activeTab === tab.id
                    ? 'border-gray-700 text-gray-900'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {message && (
            <div className={`mb-4 p-3 rounded ${
              message.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
            }`}>
              {message.text}
            </div>
          )}

          {/* General Tab */}
          {activeTab === 'general' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold mb-4">API Configuration</h2>
                
                <form onSubmit={handleSaveApiKey} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Rebrickable API Key
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="password"
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder="Enter new API key (write-only)"
                        className="flex-1 px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-gray-500"
                      />
                      <button
                        type="submit"
                        disabled={savingApiKey || !apiKey.trim()}
                        className="px-6 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 disabled:bg-gray-400 transition font-semibold"
                      >
                        {savingApiKey ? 'Updating...' : 'Update'}
                      </button>
                    </div>
                    <p className="text-sm text-gray-500 mt-1">
                      For security, the API key is never displayed. Enter a new key to update it.
                    </p>
                  </div>
                </form>
              </div>

              <div className="pt-6 border-t border-gray-200">
                <h2 className="text-xl font-bold mb-4">System Paths</h2>
                
                <div className="bg-gray-50 p-4 rounded space-y-3">
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase">LDraw Library Path</p>
                    <p className="text-sm font-mono text-gray-700">{envPaths.ldraw_library_path}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase">Cache Directory</p>
                    <p className="text-sm font-mono text-gray-700">{envPaths.cache_dir}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500 uppercase">Database Path</p>
                    <p className="text-sm font-mono text-gray-700">{envPaths.database_path}</p>
                  </div>
                  <p className="text-xs text-gray-400 mt-2">
                    These paths are configured via environment variables and cannot be changed at runtime.
                  </p>
                </div>
              </div>

              <div className="pt-6 border-t border-gray-200">
                <h2 className="text-xl font-bold mb-4">Cache management</h2>
                <p className="text-sm text-gray-600 mb-3">Manage STL, Rebrickable, part preview, LDraw, and search history in the Cache tab.</p>
                <button type="button" onClick={() => selectTab('cache')} className="inline-block px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700">Open Cache tab</button>
                <ul className="mt-2 text-sm text-gray-600 space-y-1">
                  <li><a href="/settings/cache#stl-cache" className="text-gray-700 hover:underline">STL cache</a></li>
                  <li><a href="/settings/cache#rebrickable-cache" className="text-gray-700 hover:underline">Rebrickable cache</a></li>
                  <li><a href="/settings/cache#preview-cache" className="text-gray-700 hover:underline">Part preview cache</a></li>
                  <li><a href="/settings/cache#ldraw-cache" className="text-gray-700 hover:underline">LDraw library</a></li>
                  <li><a href="/settings/cache#search-history-cache" className="text-gray-700 hover:underline">Search history</a></li>
                </ul>
              </div>
            </div>
          )}

          {/* Build & rotation Tab */}
          {activeTab === 'build' && (
            <div className="space-y-6">
              <form onSubmit={handleSaveSettings} className="space-y-6">
                <div>
                  <h2 className="text-xl font-bold mb-4">Build plate and spacing</h2>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">Plate width (mm)</label>
                      <input type="number" value={settings.default_plate_width} onChange={(e) => handleChange('default_plate_width', e.target.value)} min={100} max={2000} className="w-full px-4 py-2 border border-gray-300 rounded" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">Plate depth (mm)</label>
                      <input type="number" value={settings.default_plate_depth} onChange={(e) => handleChange('default_plate_depth', e.target.value)} min={100} max={2000} className="w-full px-4 py-2 border border-gray-300 rounded" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">Plate height (mm)</label>
                      <input type="number" value={settings.default_plate_height} onChange={(e) => handleChange('default_plate_height', e.target.value)} min={100} max={2000} className="w-full px-4 py-2 border border-gray-300 rounded" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">Part spacing (mm)</label>
                      <input type="number" value={settings.part_spacing} onChange={(e) => handleChange('part_spacing', e.target.value)} min={1} max={10} className="w-full px-4 py-2 border border-gray-300 rounded" />
                    </div>
                  </div>
                </div>

                <div className="pt-6 border-t border-gray-200">
                  <h2 className="text-xl font-bold mb-4">Rotation (X, Y, Z degrees)</h2>
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded mb-4">
                    <div>
                      <label htmlFor="rotationEnabled" className="text-sm font-medium block mb-1">Enable rotation</label>
                      <p className="text-xs text-gray-500">Apply the same rotation to all parts</p>
                    </div>
                    <input type="checkbox" id="rotationEnabled" checked={settings.rotation_enabled} onChange={(e) => handleChange('rotation_enabled', e.target.checked)} className="w-6 h-6 text-gray-600 border-gray-300 rounded focus:ring-gray-500" />
                  </div>
                  {settings.rotation_enabled && (
                    <div className="grid grid-cols-3 gap-4 mb-4">
                      <div><label className="block text-sm font-medium mb-1">X</label><input type="number" step="any" min={-360} max={360} value={settings.rotation_x} onChange={(e) => handleChange('rotation_x', e.target.value)} className="w-full px-4 py-2 border border-gray-300 rounded" /></div>
                      <div><label className="block text-sm font-medium mb-1">Y</label><input type="number" step="any" min={-360} max={360} value={settings.rotation_y} onChange={(e) => handleChange('rotation_y', e.target.value)} className="w-full px-4 py-2 border border-gray-300 rounded" /></div>
                      <div><label className="block text-sm font-medium mb-1">Z</label><input type="number" step="any" min={-360} max={360} value={settings.rotation_z} onChange={(e) => handleChange('rotation_z', e.target.value)} className="w-full px-4 py-2 border border-gray-300 rounded" /></div>
                    </div>
                  )}
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded">
                    <div>
                      <label htmlFor="matchPreview" className="text-sm font-medium block mb-1">Default orientation (match preview)</label>
                      <p className="text-xs text-gray-500">When rotation is off, apply X=-90° so STL matches part preview (studs up).</p>
                    </div>
                    <input type="checkbox" id="matchPreview" checked={settings.default_orientation_match_preview !== false} onChange={(e) => handleChange('default_orientation_match_preview', e.target.checked)} className="w-6 h-6 text-gray-600 border-gray-300 rounded focus:ring-gray-500" />
                  </div>
                </div>

                <div className="pt-6 border-t border-gray-200">
                  <h2 className="text-xl font-bold mb-4">STL scale factor</h2>
                  <input type="number" step="0.01" value={settings.stl_scale_factor} onChange={(e) => handleChange('stl_scale_factor', e.target.value)} min={0.01} max={100} className="w-full max-w-xs px-4 py-2 border border-gray-300 rounded" />
                  <p className="text-sm text-gray-500 mt-1">Default: 10 (LDView cm to mm). Calibration: part 3034 ≈ 16×64×3.2 mm. Changing clears STL cache.</p>
                </div>

                <div className="pt-6 border-t border-gray-200">
                  <h2 className="text-xl font-bold mb-4">Part previews</h2>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={settings.auto_generate_part_previews !== false} onChange={(e) => handleChange('auto_generate_part_previews', e.target.checked)} className="w-5 h-5 rounded border-gray-300 text-gray-600 focus:ring-gray-500" />
                    <span>Auto-generate part previews</span>
                  </label>
                  <p className="text-sm text-gray-500 mt-1"><a href="/settings/cache#preview-cache" className="text-gray-700 hover:underline">Manage part preview cache</a></p>
                </div>

                <button type="submit" disabled={saving} className="w-full px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:bg-gray-400 font-semibold">
                  {saving ? 'Saving...' : 'Save settings'}
                </button>
              </form>
            </div>
          )}

          {/* Cache Tab */}
          {activeTab === 'cache' && (
            <div>
              <p className="text-sm text-gray-600 mb-4">Manage STL, Rebrickable, part preview, LDraw, and search history caches.</p>
              <CacheManagementContent />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default SettingsPage
