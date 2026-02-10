import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import CacheManagementContent from '../components/CacheManagementContent'

function SettingsPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [activeTab, setActiveTab] = useState(() => {
    if (typeof window === 'undefined') return 'general'
    const p = window.location.pathname
    if (p === '/settings/cache') return 'cache'
    if (p === '/settings/database') return 'database'
    return 'general'
  })
  const [settings, setSettings] = useState({
    default_plate_width: 220,
    default_plate_depth: 220,
    default_plate_height: 250,
    part_spacing: 2,
    stl_scale_factor: 1.0,
    rotation_enabled: false,
    rotation_x: 0,
    rotation_y: 0,
    rotation_z: 0,
    default_orientation_match_preview: true,
    auto_generate_part_previews: true,
    ldview_allow_primitive_substitution: true,
    ldview_use_quality_studs: true,
    ldview_curve_quality: 2,
    ldview_seams: false,
    ldview_seam_width: 0,
    ldview_bfc: true,
    ldview_bounding_boxes_only: false,
    ldview_show_highlight_lines: false,
    ldview_polygon_offset: true,
    ldview_edge_thickness: 0,
    ldview_line_smoothing: false,
    ldview_black_highlights: false,
    ldview_conditional_highlights: false,
    ldview_wireframe: false,
    ldview_wireframe_thickness: 0,
    ldview_remove_hidden_lines: false,
    ldview_texture_studs: true,
    ldview_texmaps: true,
    ldview_hi_res_primitives: false,
    ldview_texture_filter_type: 9987,
    ldview_aniso_level: 0,
    ldview_texture_offset_factor: 5,
    ldview_lighting: true,
    ldview_use_quality_lighting: false,
    ldview_use_specular: true,
    ldview_subdued_lighting: false,
    ldview_perform_smoothing: true,
    ldview_use_flat_shading: false,
    ldview_antialias: 0,
    ldview_process_ldconfig: true,
    ldview_sort_transparent: true,
    ldview_use_stipple: false,
    ldview_memory_usage: 2,
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
  const [databaseInfo, setDatabaseInfo] = useState(null)
  const [databaseInfoLoading, setDatabaseInfoLoading] = useState(false)
  const [scaleInputStr, setScaleInputStr] = useState('1')
  const [ldviewAdvancedOpen, setLdviewAdvancedOpen] = useState(false)
  useEffect(() => {
    fetchSettings()
  }, [])
  const fetchDatabaseInfo = async () => {
    setDatabaseInfoLoading(true)
    try {
      const response = await fetch('/api/settings/database')
      if (response.ok) {
        const data = await response.json()
        setDatabaseInfo(data)
      }
    } catch (err) {
      console.error('Failed to fetch database info:', err)
    } finally {
      setDatabaseInfoLoading(false)
    }
  }
  useEffect(() => {
    if (activeTab === 'database') fetchDatabaseInfo()
  }, [activeTab])
  useEffect(() => {
    if (location.pathname === '/settings/cache') setActiveTab('cache')
    else if (location.pathname === '/settings/database') setActiveTab('database')
  }, [location.pathname])

  const fetchSettings = async () => {
    try {
      const response = await fetch('/api/settings')
      if (response.ok) {
        const data = await response.json()
        const scale = parseFloat(data.stl_scale_factor) || 1.0
        setSettings({
          ...data,
          stl_scale_factor: scale,
          rotation_x: parseFloat(data.rotation_x) || 0,
          rotation_y: parseFloat(data.rotation_y) || 0,
          rotation_z: parseFloat(data.rotation_z) || 0,
        })
        setScaleInputStr(String(scale))
      }
    } catch (err) {
      console.error('Failed to fetch settings:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveSettings = async (e) => {
    e.preventDefault()

    const scaleParsed = parseFloat(scaleInputStr)
    if (Number.isNaN(scaleParsed) || scaleParsed < 0.01 || scaleParsed > 10) {
      setMessage({ type: 'error', text: 'Scale must be a number between 0.01 and 10.' })
      return
    }

    setSaving(true)
    setMessage(null)

    try {
      const response = await fetch('/api/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...settings,
          stl_scale_factor: scaleParsed,
          rotation_x: Number(settings.rotation_x) || 0,
          rotation_y: Number(settings.rotation_y) || 0,
          rotation_z: Number(settings.rotation_z) || 0,
        }),
      })

      if (response.ok) {
        const data = await response.json()
        const saved = data.settings || {}
        const savedScale = parseFloat(saved.stl_scale_factor)
        setScaleInputStr(Number.isNaN(savedScale) ? String(scaleParsed) : String(savedScale))
        setSettings(prev => ({ ...prev, ...saved, stl_scale_factor: Number.isNaN(savedScale) ? scaleParsed : savedScale }))
        if (data.cache_cleared) {
          setMessage({ type: 'success', text: 'Settings saved! STL cache was cleared.' })
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
    if (['rotation_x', 'rotation_y', 'rotation_z'].includes(field)) {
      const val = clampRotation(value)
      setSettings(prev => ({ ...prev, [field]: val }))
    } else if (field.startsWith('ldview_')) {
      if (['ldview_allow_primitive_substitution', 'ldview_use_quality_studs', 'ldview_seams', 'ldview_bfc', 'ldview_bounding_boxes_only',
           'ldview_show_highlight_lines', 'ldview_polygon_offset', 'ldview_line_smoothing', 'ldview_black_highlights', 'ldview_conditional_highlights',
           'ldview_wireframe', 'ldview_remove_hidden_lines', 'ldview_texture_studs', 'ldview_texmaps', 'ldview_hi_res_primitives',
           'ldview_lighting', 'ldview_use_quality_lighting', 'ldview_use_specular', 'ldview_subdued_lighting', 'ldview_perform_smoothing',
           'ldview_use_flat_shading', 'ldview_process_ldconfig', 'ldview_sort_transparent', 'ldview_use_stipple'].includes(field)) {
        setSettings(prev => ({ ...prev, [field]: !!value }))
      } else if (['ldview_edge_thickness', 'ldview_wireframe_thickness', 'ldview_texture_offset_factor'].includes(field)) {
        const n = parseFloat(value)
        setSettings(prev => ({ ...prev, [field]: Number.isNaN(n) ? 0 : n }))
      } else {
        const n = parseInt(value, 10)
        setSettings(prev => ({ ...prev, [field]: Number.isNaN(n) ? 0 : n }))
      }
    } else if (field === 'rotation_enabled' || field === 'auto_generate_part_previews' || field === 'default_orientation_match_preview') {
      setSettings(prev => ({ ...prev, [field]: value }))
    } else {
      setSettings(prev => ({ ...prev, [field]: parseInt(value) }))
    }
  }

  if (loading) {
    return <div className="text-center py-8 text-dk-5">Loading...</div>
  }

  const tabs = [
    { id: 'general', label: 'General' },
    { id: 'parts', label: 'Part' },
    { id: 'ldview', label: 'LDView' },
    { id: 'cache', label: 'Cache' },
    { id: 'database', label: 'Database' },
  ]

  const LDVIEW_DEFAULTS = {
    ldview_allow_primitive_substitution: true,
    ldview_use_quality_studs: true,
    ldview_curve_quality: 2,
    ldview_seams: false,
    ldview_seam_width: 0,
    ldview_bfc: true,
    ldview_bounding_boxes_only: false,
    ldview_show_highlight_lines: false,
    ldview_polygon_offset: true,
    ldview_edge_thickness: 0,
    ldview_line_smoothing: false,
    ldview_black_highlights: false,
    ldview_conditional_highlights: false,
    ldview_wireframe: false,
    ldview_wireframe_thickness: 0,
    ldview_remove_hidden_lines: false,
    ldview_texture_studs: true,
    ldview_texmaps: true,
    ldview_hi_res_primitives: false,
    ldview_texture_filter_type: 9987,
    ldview_aniso_level: 0,
    ldview_texture_offset_factor: 5,
    ldview_lighting: true,
    ldview_use_quality_lighting: false,
    ldview_use_specular: true,
    ldview_subdued_lighting: false,
    ldview_perform_smoothing: true,
    ldview_use_flat_shading: false,
    ldview_antialias: 0,
    ldview_process_ldconfig: true,
    ldview_sort_transparent: true,
    ldview_use_stipple: false,
    ldview_memory_usage: 2,
  }

  const BASIC_LDVIEW_KEYS = ['ldview_use_quality_studs', 'ldview_antialias', 'ldview_curve_quality', 'ldview_memory_usage', 'ldview_line_smoothing']

  const ldviewSettings = [
    { key: 'ldview_allow_primitive_substitution', label: 'Allow primitive substitution', impact: 'STL + Preview', type: 'checkbox', perf: false },
    { key: 'ldview_use_quality_studs', label: 'Quality studs', impact: 'STL + Preview', type: 'checkbox', perf: false },
    { key: 'ldview_curve_quality', label: 'Curve quality (1–12)', impact: 'STL + Preview', type: 'number', min: 1, max: 12, perf: true, perfNote: 'High values may be slow' },
    { key: 'ldview_seams', label: 'Seams', impact: 'STL', type: 'checkbox', perf: false },
    { key: 'ldview_seam_width', label: 'Seam width (0–500)', impact: 'STL', type: 'number', min: 0, max: 500, perf: false },
    { key: 'ldview_bfc', label: 'BFC (back-face culling)', impact: 'STL + Preview', type: 'checkbox', perf: false },
    { key: 'ldview_bounding_boxes_only', label: 'Bounding boxes only', impact: 'STL + Preview', type: 'checkbox', perf: false },
    { key: 'ldview_show_highlight_lines', label: 'Show highlight lines (edges)', impact: 'Preview', type: 'checkbox', perf: false },
    { key: 'ldview_polygon_offset', label: 'Polygon offset (edge depth)', impact: 'Preview', type: 'checkbox', perf: false },
    { key: 'ldview_edge_thickness', label: 'Edge thickness (0–5)', impact: 'Preview', type: 'number', min: 0, max: 5, step: 0.5, perf: false },
    { key: 'ldview_line_smoothing', label: 'Line smoothing (antialiased lines)', impact: 'Preview', type: 'checkbox', perf: true },
    { key: 'ldview_black_highlights', label: 'Black highlights', impact: 'Preview', type: 'checkbox', perf: false },
    { key: 'ldview_conditional_highlights', label: 'Conditional highlights', impact: 'Preview', type: 'checkbox', perf: false },
    { key: 'ldview_wireframe', label: 'Wireframe', impact: 'Preview', type: 'checkbox', perf: false },
    { key: 'ldview_wireframe_thickness', label: 'Wireframe thickness (0–5)', impact: 'Preview', type: 'number', min: 0, max: 5, step: 0.5, perf: false },
    { key: 'ldview_remove_hidden_lines', label: 'Remove hidden lines', impact: 'Preview', type: 'checkbox', perf: false },
    { key: 'ldview_texture_studs', label: 'Texture studs', impact: 'Preview', type: 'checkbox', perf: false },
    { key: 'ldview_texmaps', label: 'Texture mapping', impact: 'Preview', type: 'checkbox', perf: false },
    { key: 'ldview_hi_res_primitives', label: 'Hi-res primitives', impact: 'STL + Preview', type: 'checkbox', perf: true },
    { key: 'ldview_texture_filter_type', label: 'Texture filter', impact: 'Preview', type: 'select', options: [{ v: 9984, l: 'Nearest' }, { v: 9985, l: 'Bilinear' }, { v: 9987, l: 'Trilinear' }], perf: false },
    { key: 'ldview_aniso_level', label: 'Aniso level', impact: 'Preview', type: 'number', min: 0, perf: false },
    { key: 'ldview_texture_offset_factor', label: 'Texture offset (1–10)', impact: 'Preview', type: 'number', min: 1, max: 10, step: 0.5, perf: false },
    { key: 'ldview_lighting', label: 'Lighting', impact: 'Preview', type: 'checkbox', perf: false },
    { key: 'ldview_use_quality_lighting', label: 'Quality lighting', impact: 'Preview', type: 'checkbox', perf: true },
    { key: 'ldview_use_specular', label: 'Specular highlight', impact: 'Preview', type: 'checkbox', perf: false },
    { key: 'ldview_subdued_lighting', label: 'Subdued lighting', impact: 'Preview', type: 'checkbox', perf: false },
    { key: 'ldview_perform_smoothing', label: 'Perform smoothing', impact: 'STL + Preview', type: 'checkbox', perf: false },
    { key: 'ldview_use_flat_shading', label: 'Flat shading', impact: 'Preview', type: 'checkbox', perf: false },
    { key: 'ldview_antialias', label: 'Antialias (FSAA)', impact: 'Preview', type: 'number', min: 0, perf: true },
    { key: 'ldview_process_ldconfig', label: 'Process ldconfig.ldr', impact: 'STL + Preview', type: 'checkbox', perf: false },
    { key: 'ldview_sort_transparent', label: 'Sort transparent', impact: 'Preview', type: 'checkbox', perf: true },
    { key: 'ldview_use_stipple', label: 'Use stipple (transparency)', impact: 'Preview', type: 'checkbox', perf: false },
    { key: 'ldview_memory_usage', label: 'Memory usage (0 Low, 1 Medium, 2 High)', impact: 'STL + Preview', type: 'number', min: 0, max: 2, perf: true, perfNote: 'Low may be slower for large models' },
  ]

  const ldviewBasicSettings = ldviewSettings.filter((s) => BASIC_LDVIEW_KEYS.includes(s.key))
  const ldviewAdvancedSettings = ldviewSettings.filter((s) => !BASIC_LDVIEW_KEYS.includes(s.key))

  const handleRestoreLdviewDefaults = () => {
    setSettings((prev) => ({ ...prev, ...LDVIEW_DEFAULTS }))
    setMessage({ type: 'success', text: 'LDView settings reset to defaults. Click Save to apply.' })
  }

  const selectTab = (id) => {
    setActiveTab(id)
    setMessage(null)
    if (id === 'cache') navigate('/settings/cache')
    else if (id === 'database') navigate('/settings/database')
    else navigate('/settings')
  }

  return (
    <div className="max-w-4xl mx-auto">
      <button onClick={() => navigate('/')} className="mb-4 px-4 py-2 bg-dk-3 text-dk-5 rounded hover:bg-mint hover:text-dk-1 transition">
        ← Back to Search
      </button>

      <div className="bg-dk-2 border border-dk-3 rounded-lg overflow-hidden">
        <div className="border-b border-dk-3">
          <nav className="flex -mb-px">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => selectTab(tab.id)}
                className={`flex-1 py-4 px-6 text-center border-b-2 font-medium text-sm transition ${
                  activeTab === tab.id ? 'border-mint text-mint' : 'border-transparent text-dk-5 hover:text-mint hover:border-dk-3'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6 text-dk-5">
          {message && (
            <div className={`mb-4 p-3 rounded ${message.type === 'success' ? 'bg-mint/20 text-mint' : 'bg-danger/20 text-danger'}`}>
              {message.text}
            </div>
          )}

          {/* General Tab */}
          {activeTab === 'general' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold mb-4 text-dk-5">API Configuration</h2>
                
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
                        className="flex-1 px-4 py-2 border border-dk-3 rounded bg-dk-1 text-dk-5 focus:outline-none focus:ring-2 focus:ring-mint"
                      />
                      <button
                        type="submit"
                        disabled={savingApiKey || !apiKey.trim()}
                        className="px-6 py-2 bg-mint text-dk-1 rounded hover:opacity-90 disabled:opacity-50 transition font-semibold"
                      >
                        {savingApiKey ? 'Updating...' : 'Update'}
                      </button>
                    </div>
                    <p className="text-sm text-dk-5/80 mt-1">
                      For security, the API key is never displayed. Enter a new key to update it.
                    </p>
                  </div>
                </form>
              </div>

              <div className="pt-6 border-t border-dk-3">
                <h2 className="text-xl font-bold mb-4 text-dk-5">Part previews</h2>
                <form onSubmit={handleSaveSettings} className="space-y-4">
                  <label className="flex items-center gap-2 cursor-pointer text-dk-5">
                    <input type="checkbox" checked={settings.auto_generate_part_previews !== false} onChange={(e) => handleChange('auto_generate_part_previews', e.target.checked)} className="w-5 h-5 rounded border-dk-3 text-mint focus:ring-mint" />
                    <span>Auto-generate part previews</span>
                  </label>
                  <p className="text-sm text-dk-5/80 mt-1"><a href="/settings/cache#preview-cache" className="text-mint hover:underline">Manage part preview cache</a></p>
                  <button type="submit" disabled={saving} className="px-6 py-2 bg-mint text-dk-1 rounded hover:opacity-90 disabled:opacity-50 transition font-semibold">
                    {saving ? 'Saving...' : 'Save settings'}
                  </button>
                </form>
              </div>

              <div className="pt-6 border-t border-dk-3">
                <h2 className="text-xl font-bold mb-4 text-dk-5">System Paths</h2>
                <div className="bg-dk-1 p-4 rounded space-y-3">
                  <div>
                    <p className="text-xs font-medium text-dk-5/80 uppercase">LDraw Library Path</p>
                    <p className="text-sm font-mono text-dk-5">{envPaths.ldraw_library_path}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-dk-5/80 uppercase">Cache Directory</p>
                    <p className="text-sm font-mono text-dk-5">{envPaths.cache_dir}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-dk-5/80 uppercase">Database Path</p>
                    <p className="text-sm font-mono text-dk-5">{envPaths.database_path}</p>
                  </div>
                  <p className="text-xs text-dk-5/70 mt-2">
                    These paths are configured via environment variables and cannot be changed at runtime.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Part Placement and Scaling Tab */}
          {activeTab === 'parts' && (
            <div className="space-y-6">
              <form onSubmit={handleSaveSettings} className="space-y-6">
                <div>
                  <h2 className="text-xl font-bold mb-4 text-dk-5">Build Plate Size and Part Spacing</h2>
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1 text-dk-5">Plate width (mm)</label>
                      <input type="number" value={settings.default_plate_width} onChange={(e) => handleChange('default_plate_width', e.target.value)} min={100} max={2000} className="w-full px-4 py-2 border border-dk-3 rounded bg-dk-1 text-dk-5" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1 text-dk-5">Plate depth (mm)</label>
                      <input type="number" value={settings.default_plate_depth} onChange={(e) => handleChange('default_plate_depth', e.target.value)} min={100} max={2000} className="w-full px-4 py-2 border border-dk-3 rounded bg-dk-1 text-dk-5" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1 text-dk-5">Plate height (mm)</label>
                      <input type="number" value={settings.default_plate_height} onChange={(e) => handleChange('default_plate_height', e.target.value)} min={100} max={2000} className="w-full px-4 py-2 border border-dk-3 rounded bg-dk-1 text-dk-5" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1 text-dk-5">Part spacing (mm)</label>
                      <input type="number" value={settings.part_spacing} onChange={(e) => handleChange('part_spacing', e.target.value)} min={1} max={10} className="w-full px-4 py-2 border border-dk-3 rounded bg-dk-1 text-dk-5" />
                    </div>
                  </div>
                </div>

                <div className="pt-6 border-t border-dk-3">
                  <h2 className="text-xl font-bold mb-4 text-dk-5">Part Rotation (X, Y, Z Degrees)</h2>
                  <div className="flex items-center justify-between p-4 bg-dk-1 rounded mb-4">
                    <div>
                      <label htmlFor="rotationEnabled" className="text-sm font-medium block mb-1 text-dk-5">Enable rotation</label>
                      <p className="text-xs text-dk-5/80">Apply the same rotation to all parts</p>
                    </div>
                    <input type="checkbox" id="rotationEnabled" checked={settings.rotation_enabled} onChange={(e) => handleChange('rotation_enabled', e.target.checked)} className="w-6 h-6 text-mint border-dk-3 rounded focus:ring-mint" />
                  </div>
                  {settings.rotation_enabled && (
                    <div className="grid grid-cols-3 gap-4 mb-4">
                      <div><label className="block text-sm font-medium mb-1">X</label><input type="number" step="any" min={-360} max={360} value={settings.rotation_x} onChange={(e) => handleChange('rotation_x', e.target.value)} className="w-full px-4 py-2 border border-dk-3 rounded bg-dk-1 text-dk-5" /></div>
                      <div><label className="block text-sm font-medium mb-1">Y</label><input type="number" step="any" min={-360} max={360} value={settings.rotation_y} onChange={(e) => handleChange('rotation_y', e.target.value)} className="w-full px-4 py-2 border border-dk-3 rounded bg-dk-1 text-dk-5" /></div>
                      <div><label className="block text-sm font-medium mb-1">Z</label><input type="number" step="any" min={-360} max={360} value={settings.rotation_z} onChange={(e) => handleChange('rotation_z', e.target.value)} className="w-full px-4 py-2 border border-dk-3 rounded bg-dk-1 text-dk-5" /></div>
                    </div>
                  )}
                  <div className="flex items-center justify-between p-4 bg-dk-1 rounded">
                    <div>
                      <label htmlFor="matchPreview" className="text-sm font-medium block mb-1 text-dk-5">Default orientation (match preview)</label>
                      <p className="text-xs text-dk-5/80">When rotation is off, apply X=-90° so STL matches part preview (studs up).</p>
                    </div>
                    <input type="checkbox" id="matchPreview" checked={settings.default_orientation_match_preview !== false} onChange={(e) => handleChange('default_orientation_match_preview', e.target.checked)} className="w-6 h-6 text-mint border-dk-3 rounded focus:ring-mint" />
                  </div>
                </div>

                <div className="pt-6 border-t border-dk-3">
                  <h2 className="text-xl font-bold mb-4 text-dk-5">STL Scaling</h2>
                  <input type="text" inputMode="decimal" value={scaleInputStr} onChange={(e) => setScaleInputStr(e.target.value)} placeholder="1" className="w-full max-w-xs px-4 py-2 border border-dk-3 rounded bg-dk-1 text-dk-5" />
                  <p className="text-sm text-dk-5/80 mt-1">Valid: 0.01–10. Default: 1.0</p>
                </div>

                <button type="submit" disabled={saving} className="w-full px-6 py-3 bg-mint text-dk-1 rounded-lg hover:opacity-90 disabled:opacity-50 font-semibold">
                  {saving ? 'Saving...' : 'Save settings'}
                </button>
              </form>
            </div>
          )}

          {/* LDView Quality Tab */}
          {activeTab === 'ldview' && (
            <div className="space-y-6">
              <p className="text-sm text-dk-5/80">
                These options control LDView when converting parts to STL and when generating part preview images. Changing any option clears the STL cache. <strong>Impact</strong> indicates which action uses the setting.
              </p>
              <form onSubmit={handleSaveSettings} className="space-y-6">
                <div className="space-y-4">
                  {ldviewBasicSettings.map(({ key, label, impact, type, perf, perfNote, min, max, step, options }) => (
                    <div key={key} className="flex flex-wrap items-center gap-2 p-3 bg-dk-1 rounded border border-dk-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <label className="text-sm font-medium text-dk-5">{label}</label>
                          <span className="text-xs px-2 py-0.5 rounded bg-dk-3 text-dk-5" title={`Affects: ${impact}`}>
                            {impact}
                          </span>
                          {perf && (
                            <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-600 dark:text-amber-400" title={perfNote || 'May be performance-intensive'}>
                              Perf
                            </span>
                          )}
                        </div>
                        {perf && perfNote && (
                          <p className="text-xs text-dk-5/70 mt-1">{perfNote}</p>
                        )}
                      </div>
                      <div className="flex-shrink-0">
                        {type === 'checkbox' ? (
                          <input
                            type="checkbox"
                            checked={!!settings[key]}
                            onChange={(e) => handleChange(key, e.target.checked)}
                            className="w-5 h-5 rounded border-dk-3 text-mint focus:ring-mint"
                          />
                        ) : type === 'select' && options ? (
                          <select
                            value={settings[key]}
                            onChange={(e) => handleChange(key, parseInt(e.target.value, 10))}
                            className="px-2 py-1.5 border border-dk-3 rounded bg-dk-2 text-dk-5 text-sm"
                          >
                            {options.map(({ v, l }) => (
                              <option key={v} value={v}>{l}</option>
                            ))}
                          </select>
                        ) : (
                          <input
                            type="number"
                            value={settings[key]}
                            onChange={(e) => handleChange(key, e.target.value)}
                            min={min}
                            max={max}
                            step={step ?? 1}
                            className="w-24 px-2 py-1.5 border border-dk-3 rounded bg-dk-2 text-dk-5 text-sm"
                          />
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="border border-dk-3 rounded-lg overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setLdviewAdvancedOpen((o) => !o)}
                    className="w-full px-4 py-3 flex items-center justify-between bg-dk-1 text-dk-5 hover:bg-dk-3/50 transition text-left font-medium"
                  >
                    <span>Advanced LDView settings</span>
                    <span className="text-dk-5/70">{ldviewAdvancedOpen ? '▼' : '▶'}</span>
                  </button>
                  {ldviewAdvancedOpen && (
                    <div className="p-4 pt-0 space-y-4 border-t border-dk-3">
                      {ldviewAdvancedSettings.map(({ key, label, impact, type, perf, perfNote, min, max, step, options }) => (
                        <div key={key} className="flex flex-wrap items-center gap-2 p-3 bg-dk-2 rounded border border-dk-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <label className="text-sm font-medium text-dk-5">{label}</label>
                              <span className="text-xs px-2 py-0.5 rounded bg-dk-3 text-dk-5" title={`Affects: ${impact}`}>
                                {impact}
                              </span>
                              {perf && (
                                <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-600 dark:text-amber-400" title={perfNote || 'May be performance-intensive'}>
                                  Perf
                                </span>
                              )}
                            </div>
                            {perf && perfNote && (
                              <p className="text-xs text-dk-5/70 mt-1">{perfNote}</p>
                            )}
                          </div>
                          <div className="flex-shrink-0">
                            {type === 'checkbox' ? (
                              <input
                                type="checkbox"
                                checked={!!settings[key]}
                                onChange={(e) => handleChange(key, e.target.checked)}
                                className="w-5 h-5 rounded border-dk-3 text-mint focus:ring-mint"
                              />
                            ) : type === 'select' && options ? (
                              <select
                                value={settings[key]}
                                onChange={(e) => handleChange(key, parseInt(e.target.value, 10))}
                                className="px-2 py-1.5 border border-dk-3 rounded bg-dk-1 text-dk-5 text-sm"
                              >
                                {options.map(({ v, l }) => (
                                  <option key={v} value={v}>{l}</option>
                                ))}
                              </select>
                            ) : (
                              <input
                                type="number"
                                value={settings[key]}
                                onChange={(e) => handleChange(key, e.target.value)}
                                min={min}
                                max={max}
                                step={step ?? 1}
                                className="w-24 px-2 py-1.5 border border-dk-3 rounded bg-dk-1 text-dk-5 text-sm"
                              />
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex flex-col sm:flex-row gap-3">
                  <button
                    type="button"
                    onClick={handleRestoreLdviewDefaults}
                    className="px-6 py-3 bg-dk-3 text-dk-5 rounded-lg hover:bg-dk-3/80 font-medium"
                  >
                    Restore LDView defaults
                  </button>
                  <button type="submit" disabled={saving} className="flex-1 px-6 py-3 bg-mint text-dk-1 rounded-lg hover:opacity-90 disabled:opacity-50 font-semibold">
                    {saving ? 'Saving...' : 'Save LDView settings'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Cache Tab */}
          {activeTab === 'cache' && (
            <div>
              <p className="text-sm text-dk-5/80 mb-4">Manage STL, Rebrickable, part preview, LDraw, and search history caches.</p>
              <CacheManagementContent />
            </div>
          )}

          {/* Database Tab */}
          {activeTab === 'database' && (
            <div className="space-y-6">
              <h2 className="text-xl font-bold text-dk-5">Database</h2>
              <p className="text-sm text-dk-5/80">View database path, applied migrations, and row counts.</p>
              {databaseInfoLoading && <p className="text-dk-5/80">Loading…</p>}
              {!databaseInfoLoading && databaseInfo && (
                <>
                  <div className="bg-dk-1 p-4 rounded">
                    <p className="text-xs font-medium text-dk-5/80 uppercase">Database path</p>
                    <p className="text-sm font-mono text-dk-5 break-all mt-1">{databaseInfo.database_path}</p>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-dk-5 mb-2">Migrations</h3>
                    {databaseInfo.migrations && databaseInfo.migrations.length > 0 ? (
                      <div className="border border-dk-3 rounded overflow-hidden">
                        <table className="w-full text-sm text-left">
                          <thead className="bg-dk-1 text-dk-5/80">
                            <tr>
                              <th className="px-4 py-2 font-medium">Revision</th>
                              <th className="px-4 py-2 font-medium">Description</th>
                              <th className="px-4 py-2 font-medium">Status</th>
                            </tr>
                          </thead>
                          <tbody className="text-dk-5">
                            {databaseInfo.migrations.map((m) => (
                              <tr key={m.revision_id} className="border-t border-dk-3">
                                <td className="px-4 py-2 font-mono">{m.revision_id}</td>
                                <td className="px-4 py-2">{m.description}</td>
                                <td className="px-4 py-2">
                                  {m.applied ? (
                                    <span className="text-mint">Applied</span>
                                  ) : (
                                    <span className="text-dk-5/70">Pending</span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <p className="text-sm text-dk-5/80">No migrations found.</p>
                    )}
                    {databaseInfo.current_revision && (
                      <p className="text-xs text-dk-5/70 mt-2">Current revision: <span className="font-mono">{databaseInfo.current_revision}</span></p>
                    )}
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-dk-5 mb-2">Table row counts</h3>
                    <div className="border border-dk-3 rounded overflow-hidden">
                      <table className="w-full text-sm text-left">
                        <thead className="bg-dk-1 text-dk-5/80">
                          <tr>
                            <th className="px-4 py-2 font-medium">Table</th>
                            <th className="px-4 py-2 font-medium">Rows</th>
                          </tr>
                        </thead>
                        <tbody className="text-dk-5">
                          {databaseInfo.table_counts && Object.entries(databaseInfo.table_counts).map(([table, count]) => (
                            <tr key={table} className="border-t border-dk-3">
                              <td className="px-4 py-2 font-mono">{table}</td>
                              <td className="px-4 py-2">{count}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              )}
              {!databaseInfoLoading && !databaseInfo && (
                <p className="text-sm text-dk-5/80">Could not load database info.</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default SettingsPage
