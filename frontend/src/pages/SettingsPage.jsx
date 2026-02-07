import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

function SettingsPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('general')
  const [settings, setSettings] = useState({
    default_plate_width: 220,
    default_plate_depth: 220,
    default_plate_height: 250,
    part_spacing: 2,
    stl_scale_factor: 16.67,
    auto_orient_enabled: true,
    orientation_strategy: 'studs_up',
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
  const [cacheStats, setCacheStats] = useState(null)
  const [clearingCache, setClearingCache] = useState(false)
  const [ldrawStats, setLdrawStats] = useState(null)
  const [clearingLdraw, setClearingLdraw] = useState(false)

  useEffect(() => {
    fetchSettings()
    fetchCacheStats()
    fetchLdrawStats()
  }, [])

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

  const fetchCacheStats = async () => {
    try {
      const response = await fetch('/api/cache/stats')
      if (response.ok) {
        const data = await response.json()
        setCacheStats(data)
      }
    } catch (err) {
      console.error('Failed to fetch cache stats:', err)
    }
  }

  const fetchLdrawStats = async () => {
    try {
      const response = await fetch('/api/ldraw/stats')
      if (response.ok) {
        const data = await response.json()
        setLdrawStats(data)
      }
    } catch (err) {
      console.error('Failed to fetch LDraw stats:', err)
    }
  }

  const handleClearCache = async () => {
    if (!confirm('Are you sure you want to clear all cached STL files? This cannot be undone.')) {
      return
    }

    setClearingCache(true)
    setMessage(null)

    try {
      const response = await fetch('/api/cache/clear', {
        method: 'DELETE',
      })

      if (response.ok) {
        const data = await response.json()
        setMessage({ type: 'success', text: data.message })
        await fetchCacheStats()
      } else {
        throw new Error('Failed to clear cache')
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setClearingCache(false)
    }
  }

  const handleClearLdraw = async () => {
    if (!confirm('Are you sure you want to clear the LDraw library? It will be re-downloaded (~40MB) on the next generation.')) {
      return
    }

    setClearingLdraw(true)
    setMessage(null)

    try {
      const response = await fetch('/api/ldraw/clear', {
        method: 'DELETE',
      })

      if (response.ok) {
        const data = await response.json()
        setMessage({ type: 'success', text: data.message })
        await fetchLdrawStats()
      } else {
        throw new Error('Failed to clear LDraw library')
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setClearingLdraw(false)
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
          setMessage({ type: 'success', text: 'Settings saved! STL cache was cleared due to scale change.' })
          await fetchCacheStats()
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

  const handleChange = (field, value) => {
    if (field === 'stl_scale_factor') {
      setSettings(prev => ({ ...prev, [field]: parseFloat(value) }))
    } else if (field === 'auto_orient_enabled') {
      setSettings(prev => ({ ...prev, [field]: value }))
    } else if (field === 'orientation_strategy') {
      setSettings(prev => ({ ...prev, [field]: value }))
    } else {
      setSettings(prev => ({ ...prev, [field]: parseInt(value) }))
    }
  }

  if (loading) {
    return <div className="text-center py-8">Loading...</div>
  }

  const tabs = [
    { id: 'general', label: 'General', icon: '⚙️' },
    { id: 'orientation', label: 'Orientation', icon: '🔄' },
    { id: 'stl', label: 'STL Processing', icon: '🔧' },
    { id: 'ldraw', label: 'LDraw Library', icon: '📦' },
  ]

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
                onClick={() => {
                  setActiveTab(tab.id)
                  setMessage(null)
                }}
                className={`flex-1 py-4 px-6 text-center border-b-2 font-medium text-sm transition ${
                  activeTab === tab.id
                    ? 'border-red-600 text-red-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
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
                        className="flex-1 px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
                      />
                      <button
                        type="submit"
                        disabled={savingApiKey || !apiKey.trim()}
                        className="px-6 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:bg-gray-400 transition font-semibold"
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
                <h2 className="text-xl font-bold mb-4">Printer Settings</h2>
                
                <form onSubmit={handleSaveSettings} className="space-y-6">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Plate Width (mm)
                      </label>
                      <input
                        type="number"
                        value={settings.default_plate_width}
                        onChange={(e) => handleChange('default_plate_width', e.target.value)}
                        min="100"
                        max="2000"
                        className="w-full px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Plate Depth (mm)
                      </label>
                      <input
                        type="number"
                        value={settings.default_plate_depth}
                        onChange={(e) => handleChange('default_plate_depth', e.target.value)}
                        min="100"
                        max="2000"
                        className="w-full px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Plate Height (mm)
                      </label>
                      <input
                        type="number"
                        value={settings.default_plate_height}
                        onChange={(e) => handleChange('default_plate_height', e.target.value)}
                        min="100"
                        max="2000"
                        className="w-full px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Part Spacing (mm)
                      </label>
                      <input
                        type="number"
                        value={settings.part_spacing}
                        onChange={(e) => handleChange('part_spacing', e.target.value)}
                        min="1"
                        max="10"
                        className="w-full px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
                      />
                    </div>
                  </div>

                  <div className="bg-blue-50 border border-blue-200 rounded p-4">
                    <p className="text-sm font-medium text-blue-900 mb-2">Common Printer Presets</p>
                    <div className="grid grid-cols-2 gap-2 text-xs text-blue-800">
                      <p>• Prusa i3 MK3S: 250 x 210 mm</p>
                      <p>• Ender 3: 220 x 220 mm</p>
                      <p>• Ender 5: 220 x 220 mm</p>
                      <p>• CR-10: 300 x 300 mm</p>
                      <p>• Prusa Mini: 180 x 180 mm</p>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={saving}
                    className="w-full px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-400 transition font-semibold"
                  >
                    {saving ? 'Saving...' : 'Save Printer Settings'}
                  </button>
                </form>
              </div>
            </div>
          )}

          {/* Orientation Tab */}
          {activeTab === 'orientation' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold mb-4">Auto-Orientation Settings</h2>
                
                <form onSubmit={handleSaveSettings} className="space-y-6">
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded">
                    <div>
                      <label htmlFor="autoOrientEnabled" className="text-sm font-medium block mb-1">
                        Enable Auto-Orientation
                      </label>
                      <p className="text-xs text-gray-500">
                        Automatically rotate parts for optimal 3D printing
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      id="autoOrientEnabled"
                      checked={settings.auto_orient_enabled}
                      onChange={(e) => handleChange('auto_orient_enabled', e.target.checked)}
                      className="w-6 h-6 text-red-600 border-gray-300 rounded focus:ring-red-500"
                    />
                  </div>

                  {settings.auto_orient_enabled && (
                    <div>
                      <label className="block text-sm font-medium mb-3">
                        Orientation Strategy
                      </label>
                      <div className="space-y-3">
                        <label className="flex items-start p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition">
                          <input
                            type="radio"
                            name="orientationStrategy"
                            value="studs_up"
                            checked={settings.orientation_strategy === 'studs_up'}
                            onChange={(e) => handleChange('orientation_strategy', e.target.value)}
                            className="w-5 h-5 text-red-600 border-gray-300 focus:ring-red-500 mt-0.5"
                          />
                          <div className="ml-3">
                            <span className="font-semibold text-gray-900">Studs Up (LEGO Optimized) ⭐</span>
                            <p className="text-sm text-gray-600 mt-1">
                              Orients LEGO bricks with studs pointing up and the flat mating surface on the build plate.
                              Provides best bed adhesion and typically requires no supports. <strong>Recommended for all LEGO parts.</strong>
                            </p>
                          </div>
                        </label>

                        <label className="flex items-start p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition">
                          <input
                            type="radio"
                            name="orientationStrategy"
                            value="flat"
                            checked={settings.orientation_strategy === 'flat'}
                            onChange={(e) => handleChange('orientation_strategy', e.target.value)}
                            className="w-5 h-5 text-red-600 border-gray-300 focus:ring-red-500 mt-0.5"
                          />
                          <div className="ml-3">
                            <span className="font-semibold text-gray-900">Flat</span>
                            <p className="text-sm text-gray-600 mt-1">
                              Lays the smallest dimension vertically for maximum stability and contact area.
                              Good for general parts but may not optimize for LEGO-specific geometry.
                            </p>
                          </div>
                        </label>

                        <label className="flex items-start p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition">
                          <input
                            type="radio"
                            name="orientationStrategy"
                            value="minimize_supports"
                            checked={settings.orientation_strategy === 'minimize_supports'}
                            onChange={(e) => handleChange('orientation_strategy', e.target.value)}
                            className="w-5 h-5 text-red-600 border-gray-300 focus:ring-red-500 mt-0.5"
                          />
                          <div className="ml-3">
                            <span className="font-semibold text-gray-900">Minimize Supports</span>
                            <p className="text-sm text-gray-600 mt-1">
                              Analyzes overhanging surfaces and chooses orientation with minimal support requirements.
                              May result in different orientations than "Flat".
                            </p>
                          </div>
                        </label>

                        <label className="flex items-start p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition">
                          <input
                            type="radio"
                            name="orientationStrategy"
                            value="original"
                            checked={settings.orientation_strategy === 'original'}
                            onChange={(e) => handleChange('orientation_strategy', e.target.value)}
                            className="w-5 h-5 text-red-600 border-gray-300 focus:ring-red-500 mt-0.5"
                          />
                          <div className="ml-3">
                            <span className="font-semibold text-gray-900">Original (No Rotation)</span>
                            <p className="text-sm text-gray-600 mt-1">
                              Use the part orientation as it appears in the LDraw library. May require heavy supports.
                            </p>
                          </div>
                        </label>
                      </div>

                      <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mt-4">
                        <p className="text-sm text-yellow-800">
                          ⚠️ <strong>Warning:</strong> Changing the orientation strategy will automatically clear all cached STL files.
                        </p>
                      </div>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={saving}
                    className="w-full px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-400 transition font-semibold"
                  >
                    {saving ? 'Saving...' : 'Save Orientation Settings'}
                  </button>
                </form>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded p-4">
                <h3 className="text-sm font-semibold text-blue-900 mb-2">About Auto-Orientation</h3>
                <p className="text-sm text-blue-800 mb-2">
                  Auto-orientation analyzes each part and rotates it to optimize for 3D printing. This can significantly reduce:
                </p>
                <ul className="text-sm text-blue-800 list-disc list-inside space-y-1">
                  <li>Support material required</li>
                  <li>Print time and cost</li>
                  <li>Risk of print failure</li>
                  <li>Post-processing cleanup time</li>
                </ul>
              </div>
            </div>
          )}

          {/* STL Processing Tab */}
          {activeTab === 'stl' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold mb-4">STL Scaling</h2>
                
                <form onSubmit={handleSaveSettings}>
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Scale Factor (multiplier for LDraw coordinates)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={settings.stl_scale_factor}
                      onChange={(e) => handleChange('stl_scale_factor', e.target.value)}
                      min="1"
                      max="100"
                      className="w-full px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
                    />
                    <p className="text-sm text-gray-500 mt-1">
                      Default: 16.67 (converts LDraw units to millimeters)
                    </p>
                    <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mt-2">
                      <p className="text-sm text-yellow-800">
                        ⚠️ <strong>Warning:</strong> Changing the scale factor will automatically clear all cached STL files.
                      </p>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={saving}
                    className="mt-4 w-full px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-400 transition font-semibold"
                  >
                    {saving ? 'Saving...' : 'Save Scale Factor'}
                  </button>
                </form>
              </div>

              <div className="pt-6 border-t border-gray-200">
                <h2 className="text-xl font-bold mb-4">STL Cache Management</h2>
                
                {cacheStats && (
                  <div className="bg-gray-50 p-4 rounded mb-4">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-gray-500">Cached Files</p>
                        <p className="text-2xl font-bold text-gray-900">{cacheStats.stl_count}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Total Size</p>
                        <p className="text-2xl font-bold text-gray-900">{cacheStats.total_size_mb.toFixed(2)} MB</p>
                      </div>
                    </div>
                    <p className="text-xs text-gray-500 mt-3 border-t border-gray-200 pt-3">
                      <strong>Directory:</strong> {cacheStats.cache_dir}
                    </p>
                  </div>
                )}
                
                <button
                  onClick={handleClearCache}
                  disabled={clearingCache}
                  className="w-full px-6 py-3 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:bg-gray-400 transition font-semibold"
                >
                  {clearingCache ? 'Clearing Cache...' : 'Clear STL Cache'}
                </button>
                <p className="text-sm text-gray-500 mt-2">
                  Clears all cached STL files. Parts will be reconverted from LDraw files on the next generation.
                </p>
              </div>
            </div>
          )}

          {/* LDraw Library Tab */}
          {activeTab === 'ldraw' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold mb-4">LDraw Parts Library</h2>
                
                {ldrawStats && (
                  <div className="bg-gray-50 p-4 rounded mb-4">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-500">Status</span>
                        <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                          ldrawStats.exists 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {ldrawStats.exists ? '✅ Downloaded' : '❌ Not Downloaded'}
                        </span>
                      </div>
                      
                      {ldrawStats.exists && (
                        <>
                          <div className="border-t border-gray-200 pt-3">
                            <div className="grid grid-cols-2 gap-4">
                              <div>
                                <p className="text-gray-500 text-sm">Part Files</p>
                                <p className="text-2xl font-bold text-gray-900">{ldrawStats.part_count.toLocaleString()}</p>
                              </div>
                              <div>
                                <p className="text-gray-500 text-sm">Library Size</p>
                                <p className="text-2xl font-bold text-gray-900">{ldrawStats.total_size_mb.toFixed(2)} MB</p>
                              </div>
                            </div>
                          </div>
                          
                          <div className="border-t border-gray-200 pt-3">
                            <p className="text-xs text-gray-500">
                              <strong>Path:</strong> {ldrawStats.library_path}
                            </p>
                          </div>
                        </>
                      )}
                      
                      {!ldrawStats.exists && (
                        <div className="border-t border-gray-200 pt-3">
                          <p className="text-sm text-gray-600">
                            The LDraw library will be automatically downloaded (~40MB) when you generate your first set.
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
                
                <button
                  onClick={handleClearLdraw}
                  disabled={clearingLdraw || !ldrawStats?.exists}
                  className="w-full px-6 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:bg-gray-400 transition font-semibold"
                >
                  {clearingLdraw ? 'Clearing Library...' : 'Clear LDraw Library'}
                </button>
                <p className="text-sm text-gray-500 mt-2">
                  Removes the LDraw parts library from disk. It will be automatically re-downloaded on the next generation.
                </p>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded p-4">
                <h3 className="text-sm font-semibold text-blue-900 mb-2">About LDraw</h3>
                <p className="text-sm text-blue-800">
                  LDraw is an open standard for LEGO CAD programs that creates 3D models using official part geometries. 
                  This library contains thousands of LEGO part definitions that are converted to STL files for 3D printing.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default SettingsPage
