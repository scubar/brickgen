import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

const WIZARD_STEPS = ['Output format', 'Build plate', 'Options', 'Rotation per part', 'Confirm']

function ProjectDetailPage() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState(null)
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [currentVersion, setCurrentVersion] = useState(null)
  const [wizardOpen, setWizardOpen] = useState(false)
  const [wizardStep, setWizardStep] = useState(0)
  const [creatingJob, setCreatingJob] = useState(false)
  const [plateWidth, setPlateWidth] = useState(220)
  const [plateDepth, setPlateDepth] = useState(220)
  const [scaleFactor, setScaleFactor] = useState(null) // null = use global default
  const [format3mf, setFormat3mf] = useState(true)
  const [formatStl, setFormatStl] = useState(true)
  const [bypassCache, setBypassCache] = useState(false)
  const [activeJobId, setActiveJobId] = useState(null)
  const [wizardGlobalSettings, setWizardGlobalSettings] = useState(null)
  const [wizardParts, setWizardParts] = useState([])
  const [perPartRotation, setPerPartRotation] = useState({})
  const [previewRotationByPart, setPreviewRotationByPart] = useState({}) // rotation actually used for preview image (updated on "Update" click)
  const [wizardPartsPage, setWizardPartsPage] = useState(1)
  const [partsList, setPartsList] = useState([])
  const [partsPage, setPartsPage] = useState(1)
  const [colorRefPage, setColorRefPage] = useState(1)
  const [deletingJobId, setDeletingJobId] = useState(null)
  const WIZARD_PARTS_PAGE_SIZE = 20
  const PARTS_PAGE_SIZE = 15
  const COLOR_REF_PAGE_SIZE = 20
  const wizardPartsTotalPages = Math.max(1, Math.ceil(wizardParts.length / WIZARD_PARTS_PAGE_SIZE))
  const wizardPartsToShow = wizardParts.slice((wizardPartsPage - 1) * WIZARD_PARTS_PAGE_SIZE, wizardPartsPage * WIZARD_PARTS_PAGE_SIZE)
  const partsTotalPages = Math.max(1, Math.ceil(partsList.length / PARTS_PAGE_SIZE))
  const partsToShow = partsList.slice((partsPage - 1) * PARTS_PAGE_SIZE, partsPage * PARTS_PAGE_SIZE)
  const partColorRefList = partsList.flatMap((p) =>
    Array.from({ length: p.quantity || 1 }, (_, i) => ({
      partId: `${p.ldraw_id || p.part_num}_${i + 1}`,
      color: p.color || '—',
      color_rgb: (p.color_rgb && String(p.color_rgb).trim()) ? String(p.color_rgb).replace(/^#/, '') : '—'
    }))
  )
  const colorRefTotalPages = Math.max(1, Math.ceil(partColorRefList.length / COLOR_REF_PAGE_SIZE))
  const colorRefToShow = partColorRefList.slice((colorRefPage - 1) * COLOR_REF_PAGE_SIZE, colorRefPage * COLOR_REF_PAGE_SIZE)

  useEffect(() => {
    fetchProject()
    fetchVersion()
  }, [projectId])

  useEffect(() => {
    if (projectId) fetchJobs()
  }, [projectId])

  useEffect(() => {
    if (project?.set_num) {
      fetch(`/api/sets/${encodeURIComponent(project.set_num)}/parts`)
        .then((r) => r.ok ? r.json() : [])
        .then(setPartsList)
        .catch(() => setPartsList([]))
    } else {
      setPartsList([])
    }
  }, [project?.set_num])

  useEffect(() => {
    setColorRefPage(1)
  }, [project?.set_num])

  useEffect(() => {
    if (!activeJobId) return
    const interval = setInterval(async () => {
      try {
        const r = await fetch(`/api/jobs/${activeJobId}`)
        if (!r.ok) return
        const j = await r.json()
        await fetchJobs()
        if (j.status === 'completed' || j.status === 'failed') setActiveJobId(null)
      } catch (e) {
        console.error(e)
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [activeJobId, projectId])

  const fetchVersion = async () => {
    try {
      const r = await fetch('/api/version')
      if (r.ok) {
        const d = await r.json()
        setCurrentVersion(d.version)
      }
    } catch (e) {
      console.error(e)
    }
  }

  const fetchProject = async () => {
    try {
      const r = await fetch(`/api/projects/${projectId}`)
      if (!r.ok) throw new Error('Project not found')
      setProject(await r.json())
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const fetchJobs = async () => {
    try {
      const r = await fetch(`/api/projects/${projectId}/jobs`)
      if (r.ok) setJobs(await r.json())
    } catch (e) {
      console.error(e)
    }
  }

  const openWizard = async () => {
    setWizardStep(0)
    setPerPartRotation({})
    setPreviewRotationByPart({})
    setWizardOpen(true)
    try {
      const [settingsRes, partsRes] = await Promise.all([
        fetch('/api/settings'),
        project?.set_num ? fetch(`/api/sets/${encodeURIComponent(project.set_num)}/parts`) : Promise.resolve(null)
      ])
      if (settingsRes?.ok) {
        const s = await settingsRes.json()
        setWizardGlobalSettings(s)
        setPlateWidth(s.default_plate_width ?? 220)
        setPlateDepth(s.default_plate_depth ?? 220)
        setScaleFactor(null) // use global default for new job
      }
      if (partsRes?.ok) {
        const partsList = await partsRes.json()
        const byId = new Map()
        partsList.forEach(p => {
          const id = p.ldraw_id || p.part_num
          if (id && !byId.has(id)) byId.set(id, { ldraw_id: id, part_num: p.part_num, name: p.name, quantity: p.quantity })
        })
        setWizardParts(Array.from(byId.values()))
      } else {
        setWizardParts([])
      }
    } catch (e) {
      console.error(e)
    }
  }

  const wizardNext = () => {
    if (wizardStep === 0 && !format3mf) setWizardStep(2)
    else setWizardStep((s) => s + 1)
  }
  const wizardBack = () => {
    if (wizardStep === 2 && !format3mf) setWizardStep(0)
    else if (wizardStep === 2) setWizardStep(1)
    else setWizardStep((s) => s - 1)
  }
  const setPartRotation = (ldrawId, axis, value) => {
    setPerPartRotation(prev => ({
      ...prev,
      [ldrawId]: {
        ...(prev[ldrawId] || { x: 0, y: 0, z: 0 }),
        [axis]: Number(value) || 0
      }
    }))
  }

  const createJob = async () => {
    setCreatingJob(true)
    try {
      const r = await fetch(`/api/projects/${projectId}/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plate_width: plateWidth,
          plate_depth: plateDepth,
          generate_3mf: format3mf,
          generate_stl: formatStl,
          bypass_cache: bypassCache,
          per_part_rotation: Object.keys(perPartRotation).length ? perPartRotation : undefined,
          scale_factor: (scaleFactor != null && scaleFactor > 0) ? scaleFactor : (wizardGlobalSettings?.stl_scale_factor ?? 10)
        })
      })
      if (!r.ok) throw new Error('Failed to create job')
      const data = await r.json()
      setActiveJobId(data.job_id)
      setWizardOpen(false)
      await fetchJobs()
    } catch (e) {
      console.error(e)
    } finally {
      setCreatingJob(false)
    }
  }

  const rerunJob = async (jobId, jobVersion) => {
    const warn = currentVersion && jobVersion && currentVersion !== jobVersion
    if (warn && !confirm('This job was created with a different BrickGen version. There may be issues; consider creating a new job instead. Re-run anyway?')) return
    try {
      const r = await fetch(`/api/jobs/${jobId}/rerun`, { method: 'POST' })
      if (r.ok) {
        await fetchJobs()
        setActiveJobId(null)
      }
    } catch (e) {
      console.error(e)
    }
  }

  const deleteJobFiles = async (jobId) => {
    if (!confirm('Remove this job\'s output file from disk?')) return
    try {
      await fetch(`/api/jobs/${jobId}/files`, { method: 'DELETE' })
      await fetchJobs()
    } catch (e) {
      console.error(e)
    }
  }

  const deleteJob = async (jobId) => {
    if (!confirm('Delete this job and its output file? This cannot be undone.')) return
    setDeletingJobId(jobId)
    try {
      const r = await fetch(`/api/jobs/${jobId}`, { method: 'DELETE' })
      if (r.ok) await fetchJobs()
    } catch (e) {
      console.error(e)
    } finally {
      setDeletingJobId(null)
    }
  }

  const deleteProject = async () => {
    if (!confirm('Delete this project and all its jobs and output files?')) return
    try {
      await fetch(`/api/projects/${projectId}`, { method: 'DELETE' })
      navigate('/projects')
    } catch (e) {
      console.error(e)
    }
  }

  if (loading || !project) return <div className="text-center py-8 text-dk-5">Loading...</div>

  return (
    <div className="max-w-4xl mx-auto">
      <button onClick={() => navigate('/projects')} className="mb-4 px-4 py-2 bg-dk-3 text-dk-5 rounded hover:bg-mint hover:text-dk-1 transition">← Projects</button>
      <div className="bg-dk-2 rounded-lg border border-dk-3 p-6 mb-6 flex items-start justify-between">
        <div className="flex gap-4">
          {project.image_url && <img src={project.image_url} alt="" className="w-24 h-24 object-contain bg-dk-1 rounded" />}
          <div>
            <h1 className="text-2xl font-bold text-dk-5">{project.name}</h1>
            <p className="text-dk-5/80">{project.set_num} {project.set_name && ` · ${project.set_name}`}</p>
          </div>
        </div>
        <button onClick={deleteProject} className="px-3 py-1 text-danger hover:text-danger/80 border border-dk-3 rounded hover:bg-dk-3">Delete project</button>
      </div>

      {partsList.length > 0 && (
        <details className="bg-dk-2 rounded-lg border border-dk-3 p-4 mb-6">
          <summary className="cursor-pointer font-semibold text-dk-5 hover:text-mint">Part list ({partsList.length} parts)</summary>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-dk-5 border-b border-dk-3">
                  <th className="pb-2 pr-2 w-20">Preview</th>
                  <th className="pb-2 pr-4">Part</th>
                  <th className="pb-2 pr-4">Name</th>
                  <th className="pb-2 pr-4">Qty</th>
                  <th className="pb-2">Color</th>
                </tr>
              </thead>
              <tbody className="text-dk-5">
                {partsToShow.map((p, i) => (
                  <tr key={(partsPage - 1) * PARTS_PAGE_SIZE + i} className="border-b border-dk-3/50">
                    <td className="py-1.5 pr-2">
                      <img
                        src={`/api/parts/preview/${encodeURIComponent(p.ldraw_id || p.part_num)}?size=128${p.color_rgb ? `&color=${encodeURIComponent(p.color_rgb)}` : ''}`}
                        alt=""
                        className="w-12 h-12 object-contain bg-dk-1 rounded"
                        onError={(e) => { e.target.style.display = 'none' }}
                      />
                    </td>
                    <td className="py-1.5 font-mono">{p.ldraw_id || p.part_num}</td>
                    <td className="py-1.5 truncate max-w-[200px]">{p.name}</td>
                    <td className="py-1.5">{p.quantity}</td>
                    <td className="py-1.5">{p.color}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {partsTotalPages > 1 && (
              <div className="flex items-center justify-between mt-2 pt-2 border-t border-dk-3">
                <button type="button" onClick={() => setPartsPage((p) => Math.max(1, p - 1))} disabled={partsPage <= 1} className="px-2 py-1 text-dk-5 border border-dk-3 rounded text-sm disabled:opacity-50">Previous</button>
                <span className="text-sm text-dk-5">Page {partsPage} of {partsTotalPages}</span>
                <button type="button" onClick={() => setPartsPage((p) => Math.min(partsTotalPages, p + 1))} disabled={partsPage >= partsTotalPages} className="px-2 py-1 text-dk-5 border border-dk-3 rounded text-sm disabled:opacity-50">Next</button>
              </div>
            )}
          </div>
        </details>
      )}

      {partColorRefList.length > 0 && (
        <details className="bg-dk-2 rounded-lg border border-dk-3 p-4 mb-6">
          <summary className="cursor-pointer font-semibold text-dk-5 hover:text-mint">Part &amp; color reference (for Bambu Studio / OrcaSlicer)</summary>
          <p className="mt-2 mb-3 text-sm text-dk-5/90">Use this list to assign filament to parts in your slicer. Part number format is <code className="bg-dk-1 px-1 rounded">LDrawId_instance</code> (e.g. 3404_1, 3404_2).</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-dk-5 border-b border-dk-3">
                  <th className="pb-2 pr-4">Part number</th>
                  <th className="pb-2 pr-4">Color</th>
                  <th className="pb-2">Hex code</th>
                </tr>
              </thead>
              <tbody className="text-dk-5">
                {colorRefToShow.map((row) => (
                  <tr key={row.partId} className="border-b border-dk-3/50">
                    <td className="py-1.5 font-mono">{row.partId}</td>
                    <td className="py-1.5">{row.color}</td>
                    <td className="py-1.5 font-mono">{row.color_rgb !== '—' ? `#${row.color_rgb}` : row.color_rgb}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {colorRefTotalPages > 1 && (
              <div className="flex items-center justify-between mt-2 pt-2 border-t border-dk-3">
                <button type="button" onClick={() => setColorRefPage((p) => Math.max(1, p - 1))} disabled={colorRefPage <= 1} className="px-2 py-1 text-dk-5 border border-dk-3 rounded text-sm disabled:opacity-50">Previous</button>
                <span className="text-sm text-dk-5">Page {colorRefPage} of {colorRefTotalPages}</span>
                <button type="button" onClick={() => setColorRefPage((p) => Math.min(colorRefTotalPages, p + 1))} disabled={colorRefPage >= colorRefTotalPages} className="px-2 py-1 text-dk-5 border border-dk-3 rounded text-sm disabled:opacity-50">Next</button>
              </div>
            )}
          </div>
        </details>
      )}

      <div className="bg-dk-2 rounded-lg border border-dk-3 p-6 mb-6">
        <h2 className="text-lg font-bold mb-4 text-dk-5">Jobs</h2>
        {jobs.some((j) => j.status === 'completed' && j.output_file?.endsWith('.3mf')) && (
          <div className="mb-4 p-3 bg-dk-1 border border-dk-3 rounded text-sm text-dk-5">
            <strong>3MF and OrcaSlicer / Bambu Studio:</strong> Colors in the 3MF are embedded for viewers like Microsoft 3D Viewer. OrcaSlicer and Bambu Studio do not preserve these colors and may show filament at index 1. Use the <strong>Part &amp; color reference</strong> section below to assign filaments to parts manually in your slicer.
          </div>
        )}
        <button onClick={openWizard} className="mb-4 px-6 py-2 bg-mint text-dk-1 rounded hover:opacity-90">New job</button>

        {jobs.length === 0 ? (
          <p className="text-dk-5/80">No jobs yet. Click &quot;New job&quot; to create one (wizard will guide you through settings).</p>
        ) : (
          <ul className="divide-y divide-dk-3">
            {jobs.map((j) => (
              <li key={j.job_id} className="py-3">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div>
                    <span className="font-medium text-dk-5">{j.job_id.slice(0, 8)}…</span>
                    <span className={`ml-2 px-2 py-0.5 rounded text-sm ${j.status === 'completed' ? 'bg-mint/20 text-mint' : j.status === 'failed' ? 'bg-danger/20 text-danger' : 'bg-dk-3 text-dk-5'}`}>{j.status}</span>
                    {j.brickgen_version && currentVersion && j.brickgen_version !== currentVersion && (
                      <span className="ml-2 text-amber-400 text-xs">(different version)</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {j.status === 'completed' && j.output_file && (
                      <a href={`/api/download/${j.job_id}`} className="px-3 py-1 bg-mint text-dk-1 rounded text-sm hover:opacity-90">Download</a>
                    )}
                    <button onClick={() => rerunJob(j.job_id, j.brickgen_version)} className="px-3 py-1 border border-dk-3 rounded text-sm text-dk-5 hover:bg-dk-3">Re-run</button>
                    {j.output_file && (
                      <button onClick={() => deleteJobFiles(j.job_id)} className="px-3 py-1 text-dk-5 border border-dk-3 rounded text-sm hover:bg-dk-3">Clear files</button>
                    )}
                    <button onClick={() => deleteJob(j.job_id)} disabled={deletingJobId === j.job_id} className="px-3 py-1 text-danger hover:text-danger/80 hover:bg-dk-3 rounded text-sm disabled:opacity-50">{deletingJobId === j.job_id ? 'Deleting…' : 'Delete job'}</button>
                  </div>
                </div>
                {(j.status === 'processing' || j.status === 'pending') && j.progress !== undefined && (
                  <div className="mt-2">
                    <div className="flex justify-between text-sm text-dk-5 mb-1">
                      <span>Progress</span>
                      <span>{j.progress}%</span>
                    </div>
                    <div className="w-full bg-dk-3 rounded-full h-1.5">
                      <div className="bg-mint h-1.5 rounded-full transition-all" style={{ width: `${j.progress}%` }} />
                    </div>
                  </div>
                )}
                {j.status === 'failed' && j.error_message && (
                  <p className="mt-2 text-sm text-danger">Error: {j.error_message}</p>
                )}
                {(j.log || j.status === 'completed' || j.status === 'failed') && (
                  <details className="mt-2">
                    <summary className="text-sm text-dk-5 cursor-pointer hover:text-mint">Job log</summary>
                    <pre className="mt-1 p-2 bg-dk-1 rounded text-xs text-left overflow-x-auto whitespace-pre-wrap font-mono text-dk-5">{j.log || 'No log entries.'}</pre>
                  </details>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {wizardOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-dk-2 border border-dk-3 rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-auto">
            <div className="p-6 border-b border-dk-3 flex items-center justify-between">
              <h3 className="text-xl font-bold text-dk-5">New job – {WIZARD_STEPS[wizardStep]}</h3>
              <button type="button" onClick={() => setWizardOpen(false)} className="text-dk-5 hover:text-mint text-2xl leading-none">×</button>
            </div>
            <div className="p-6 text-dk-5">
              {wizardStep === 0 && (
                <div className="space-y-4">
                  <p className="text-sm text-dk-5">Choose output types. At least one must be selected.</p>
                  <div className="space-y-2">
                    <label className="flex items-start gap-3 p-3 border border-dk-3 rounded cursor-pointer hover:bg-dk-3/50">
                      <input type="checkbox" checked={format3mf} onChange={(e) => setFormat3mf(e.target.checked)} className="mt-1 rounded text-mint" />
                      <div>
                        <span className="font-medium">3MF</span>
                        <p className="text-sm text-dk-5/90">Parts pre-arranged on build plate (recommended for printing)</p>
                        <p className="text-xs text-dk-5/70 mt-0.5">Color in 3MF is not preserved in OrcaSlicer/Bambu Studio; use the Part &amp; color reference on this page to set filament per part.</p>
                      </div>
                    </label>
                    <label className="flex items-start gap-3 p-3 border border-dk-3 rounded cursor-pointer hover:bg-dk-3/50">
                      <input type="checkbox" checked={formatStl} onChange={(e) => setFormatStl(e.target.checked)} className="mt-1 rounded text-mint" />
                      <div>
                        <span className="font-medium">STL</span>
                        <p className="text-sm text-dk-5/90">Individual STL files (in a <code className="bg-dk-1 px-1 rounded">stls/</code> folder when bundled)</p>
                      </div>
                    </label>
                  </div>
                  {!format3mf && !formatStl && <p className="text-sm text-danger">Select at least one output type.</p>}
                  {wizardGlobalSettings && (
                    <div className="bg-dk-1 border border-dk-3 rounded p-3 text-sm text-dk-5">
                      <p className="font-medium mb-1">Current global settings (read-only)</p>
                      <p>Scale: {wizardGlobalSettings.stl_scale_factor ?? 10} (STL in mm; calibrated for parts 3034 / 3404)</p>
                      <p>Rotation: {wizardGlobalSettings.rotation_enabled ? `X=${wizardGlobalSettings.rotation_x ?? 0}°, Y=${wizardGlobalSettings.rotation_y ?? 0}°, Z=${wizardGlobalSettings.rotation_z ?? 0}°` : 'Off'}</p>
                      <button type="button" onClick={() => { setWizardOpen(false); navigate('/settings'); }} className="text-mint hover:underline mt-1">Change in Settings</button>
                    </div>
                  )}
                </div>
              )}
              {wizardStep === 1 && (
                <div className="space-y-4">
                  <p className="text-sm text-dk-5">Set your build plate size (from global settings by default). Only used for 3MF output.</p>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1 text-dk-5">Plate width (mm)</label>
                      <input type="number" value={plateWidth} onChange={(e) => setPlateWidth(Number(e.target.value))} min={100} max={2000} className="w-full px-3 py-2 border border-dk-3 rounded bg-dk-1 text-dk-5" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1 text-dk-5">Plate depth (mm)</label>
                      <input type="number" value={plateDepth} onChange={(e) => setPlateDepth(Number(e.target.value))} min={100} max={2000} className="w-full px-3 py-2 border border-dk-3 rounded bg-dk-1 text-dk-5" />
                    </div>
                  </div>
                </div>
              )}
              {wizardStep === 2 && (
                <div className="space-y-4">
                  <label className="flex items-center gap-2 cursor-pointer text-dk-5">
                    <input type="checkbox" checked={bypassCache} onChange={(e) => setBypassCache(e.target.checked)} className="rounded text-mint" />
                    <span>Bypass cache (reconvert all parts from LDraw)</span>
                  </label>
                  <p className="text-sm text-dk-5/80">Leave unchecked to use cached STLs when possible.</p>
                  <div>
                    <label className="block text-sm font-medium mb-1 text-dk-5">STL scale factor (optional)</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0.01"
                      max="100"
                      placeholder={wizardGlobalSettings ? `Default: ${wizardGlobalSettings.stl_scale_factor ?? 10}` : 'Default: 10'}
                      value={scaleFactor ?? ''}
                      onChange={(e) => setScaleFactor(e.target.value === '' ? null : Number(e.target.value))}
                      className="w-full px-3 py-2 border border-dk-3 rounded bg-dk-1 text-dk-5"
                    />
                    <p className="text-xs text-dk-5/70 mt-1">Leave empty to use global default. Affects part size in mm (e.g. 10 = LDView cm to mm).</p>
                  </div>
                  {wizardGlobalSettings && (
                    <div className="bg-dk-1 border border-dk-3 rounded p-3 text-sm text-dk-5">
                      <p className="font-medium mb-1">Rotation (read-only)</p>
                      <p>Rotation: {wizardGlobalSettings.rotation_enabled ? `X=${wizardGlobalSettings.rotation_x ?? 0}°, Y=${wizardGlobalSettings.rotation_y ?? 0}°, Z=${wizardGlobalSettings.rotation_z ?? 0}°` : 'Off'}</p>
                    </div>
                  )}
                </div>
              )}
              {wizardStep === 3 && (() => {
                const getDefaultRotation = () => {
                  if (wizardGlobalSettings?.rotation_enabled) {
                    return { rx: Number(wizardGlobalSettings.rotation_x) || 0, ry: Number(wizardGlobalSettings.rotation_y) || 0, rz: Number(wizardGlobalSettings.rotation_z) || 0 }
                  }
                  if (wizardGlobalSettings?.default_orientation_match_preview !== false) return { rx: -90, ry: 0, rz: 0 }
                  return { rx: 0, ry: 0, rz: 0 }
                }
                const getEffectiveRotation = (part) => {
                  const rot = perPartRotation[part.ldraw_id] || { x: 0, y: 0, z: 0 }
                  const hasPerPart = (rot.x != null && rot.x !== '') || (rot.y != null && rot.y !== '') || (rot.z != null && rot.z !== '')
                  if (hasPerPart) return { rx: Number(rot.x) || 0, ry: Number(rot.y) || 0, rz: Number(rot.z) || 0 }
                  return getDefaultRotation()
                }
                const getPreviewRotation = (part) => previewRotationByPart[part.ldraw_id] ?? getDefaultRotation()
                const rotationEqual = (a, b) => a.rx === b.rx && a.ry === b.ry && a.rz === b.rz
                return (
                  <div className="space-y-3">
                    <p className="text-sm text-dk-5/80">Optional: set rotation (X, Y, Z degrees) per part. Parts not listed use global rotation from Settings. Click &quot;Update&quot; to refresh the preview after changing rotation.</p>
                    <div className="max-h-80 overflow-y-auto space-y-3 border border-dk-3 rounded p-2 bg-dk-1">
                      {wizardParts.length === 0 ? (
                        <p className="text-sm text-dk-5/80">No parts loaded. Parts will use global rotation.</p>
                      ) : (
                        wizardPartsToShow.map((p) => {
                          const rot = perPartRotation[p.ldraw_id] || { x: 0, y: 0, z: 0 }
                          const effective = getEffectiveRotation(p)
                          const previewRot = getPreviewRotation(p)
                          const needsUpdate = !rotationEqual(effective, previewRot)
                          const previewUrl = `/api/parts/preview/${encodeURIComponent(p.ldraw_id)}?size=256&rotation_x=${previewRot.rx}&rotation_y=${previewRot.ry}&rotation_z=${previewRot.rz}`
                          return (
                            <div key={p.ldraw_id} className="flex items-center gap-3 p-2 bg-white rounded border">
                              <img src={previewUrl} alt="" className="w-20 h-20 object-contain bg-dk-2 rounded flex-shrink-0" onError={(e) => { e.target.style.display = 'none' }} />
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium truncate">{p.ldraw_id} {p.name && `· ${p.name}`}</p>
                                <div className="flex gap-2 mt-1 flex-wrap items-center">
                                  <input type="number" placeholder="X" value={rot.x || ''} onChange={(e) => setPartRotation(p.ldraw_id, 'x', e.target.value)} className="w-14 px-1 py-0.5 text-sm border rounded" />
                                  <input type="number" placeholder="Y" value={rot.y || ''} onChange={(e) => setPartRotation(p.ldraw_id, 'y', e.target.value)} className="w-14 px-1 py-0.5 text-sm border rounded" />
                                  <input type="number" placeholder="Z" value={rot.z || ''} onChange={(e) => setPartRotation(p.ldraw_id, 'z', e.target.value)} className="w-14 px-1 py-0.5 text-sm border rounded" />
                                  {needsUpdate && (
                                    <button
                                      type="button"
                                      onClick={() => setPreviewRotationByPart(prev => ({ ...prev, [p.ldraw_id]: getEffectiveRotation(p) }))}
                                      className="px-2 py-1 text-xs bg-mint text-dk-1 rounded hover:opacity-90"
                                    >
                                      Update preview
                                    </button>
                                  )}
                                </div>
                              </div>
                            </div>
                          )
                        })
                      )}
                    </div>
                  {wizardParts.length > WIZARD_PARTS_PAGE_SIZE && (
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-dk-5/80">Page {wizardPartsPage} of {wizardPartsTotalPages}</span>
                      <div className="flex gap-2">
                        <button type="button" onClick={() => setWizardPartsPage(p => Math.max(1, p - 1))} disabled={wizardPartsPage <= 1} className="px-2 py-1 border rounded disabled:opacity-50">Previous</button>
                        <button type="button" onClick={() => setWizardPartsPage(p => Math.min(wizardPartsTotalPages, p + 1))} disabled={wizardPartsPage >= wizardPartsTotalPages} className="px-2 py-1 border rounded disabled:opacity-50">Next</button>
                      </div>
                    </div>
                  )}
                </div>
                )
              })()}
              {wizardStep === 4 && (
                <div className="space-y-3 text-sm text-dk-5">
                  {format3mf && <p><strong>Build plate:</strong> {plateWidth} × {plateDepth} mm</p>}
                  <p><strong>Output:</strong> {[format3mf && '3MF', formatStl && 'STL (in stls/)'].filter(Boolean).join(', ') || 'None'}</p>
                  <p><strong>Bypass cache:</strong> {bypassCache ? 'Yes' : 'No'}</p>
                  {Object.keys(perPartRotation).length > 0 && (
                    <p><strong>Per-part rotation:</strong> {Object.keys(perPartRotation).length} part(s) customized</p>
                  )}
                  {wizardGlobalSettings && (
                    <p><strong>Scale:</strong> {scaleFactor != null ? scaleFactor : `Default ${wizardGlobalSettings.stl_scale_factor ?? 10}`} · <strong>Rotation:</strong> {wizardGlobalSettings.rotation_enabled ? `X=${wizardGlobalSettings.rotation_x ?? 0}°, Y=${wizardGlobalSettings.rotation_y ?? 0}°, Z=${wizardGlobalSettings.rotation_z ?? 0}°` : 'Off'}</p>
                  )}
                </div>
              )}
            </div>
            <div className="p-6 border-t border-dk-3 flex justify-between">
              <div>
                {wizardStep > 0 && (
                  <button type="button" onClick={wizardBack} className="px-4 py-2 border border-dk-3 rounded text-dk-5 hover:bg-dk-3">Back</button>
                )}
              </div>
              <div className="flex gap-2">
                {wizardStep < WIZARD_STEPS.length - 1 ? (
                  <button
                    type="button"
                    onClick={wizardNext}
                    disabled={wizardStep === 0 && !format3mf && !formatStl}
                    className="px-6 py-2 bg-mint text-dk-1 rounded hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                ) : (
                  <button type="button" onClick={createJob} disabled={creatingJob} className="px-6 py-2 bg-mint text-dk-1 rounded hover:opacity-90 disabled:opacity-50">
                    {creatingJob ? 'Creating…' : 'Create job'}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ProjectDetailPage
