import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { apiFetch } from '../api'
import { Pagination, DataTable, LoadingState, EmptyState, ProgressBar, Badge, Button } from '../components/ui'

const WIZARD_STEPS = ['Output', 'Build Plate', 'Options', 'Per Part Rotation', 'Confirm']

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
  const [plateWidth, setPlateWidth] = useState(250)
  const [plateDepth, setPlateDepth] = useState(250)
  const [plateHeight, setPlateHeight] = useState(250)
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
  const [cancellingJobId, setCancellingJobId] = useState(null)
  const WIZARD_PARTS_PAGE_SIZE = 5
  const PARTS_PAGE_SIZE = 5
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

  const formatScale = (v) => {
    const n = parseFloat(v)
    if (Number.isNaN(n)) return '1.0'
    return n === Math.round(n) ? Number(n).toFixed(1) : String(n)
  }

  useEffect(() => {
    fetchProject()
    fetchVersion()
  }, [projectId])

  useEffect(() => {
    if (projectId) fetchJobs()
  }, [projectId])

  useEffect(() => {
    if (project?.set_num) {
      apiFetch(`/api/sets/${encodeURIComponent(project.set_num)}/parts`)
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

  const activeJobIdRef = useRef(null)
  activeJobIdRef.current = activeJobId
  useEffect(() => {
    if (!activeJobId) return
    const jobId = activeJobId
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/jobs/${encodeURIComponent(jobId)}/ws`
    let ws = null
    let reconnectAttempts = 0
    let reconnectTimer = null
    let pollingTimer = null
    let shouldReconnect = true
    const MAX_RECONNECT_ATTEMPTS = 5
    const INITIAL_BACKOFF_MS = 1000
    const MAX_BACKOFF_MS = 16000
    const POLLING_INTERVAL_MS = 2000

    const calculateBackoff = (attemptNumber) => {
      return Math.min(INITIAL_BACKOFF_MS * Math.pow(2, attemptNumber - 1), MAX_BACKOFF_MS)
    }

    const createPlaceholderJob = (jobId, statusData) => {
      const nowIso = new Date().toISOString()
      return {
        job_id: jobId,
        set_num: '',
        status: statusData.status,
        progress: statusData.progressValue,
        error_message: statusData.error_message ?? null,
        log: statusData.log ?? null,
        output_file: null,
        brickgen_version: null,
        created_at: nowIso,
        updated_at: nowIso
      }
    }

    const updateJobProgress = (progress) => {
      const { status, progress: progressValue, error_message, log } = progress
      setJobs(prev => {
        const idx = prev.findIndex(job => job.job_id === jobId)
        const updated = { status, progress: progressValue, error_message: error_message ?? null, log: log ?? null }
        if (idx >= 0) return prev.map((job, i) => (i === idx ? { ...job, ...updated } : job))
        // Create a placeholder job entry for jobs not yet in the list
        return [createPlaceholderJob(jobId, { status, progressValue, error_message, log }), ...prev]
      })
    }

    const checkJobCompletion = (status) => {
      if (status === 'completed' || status === 'failed') {
        shouldReconnect = false
        setActiveJobId(null)
        ws?.close()
        clearTimeout(reconnectTimer)
        clearInterval(pollingTimer)
apiFetch(`/api/jobs/${jobId}`)
        .then((r) => r.ok ? r.json() : null)
          .then((j) => {
            if (j) setJobs(prev => prev.map(job => job.job_id === jobId ? { ...job, ...j, job_id: j.job_id ?? jobId } : job))
          })
          .finally(fetchJobs)
      }
    }

    const startPolling = () => {
      if (pollingTimer) return
      console.log(`Starting polling fallback for job ${jobId}`)
      pollingTimer = setInterval(async () => {
        if (activeJobIdRef.current !== jobId) {
          clearInterval(pollingTimer)
          return
        }
        try {
          const r = await apiFetch(`/api/jobs/${jobId}/progress`)
          if (r.ok) {
            const p = await r.json()
            updateJobProgress(p)
            checkJobCompletion(p.status)
          } else if (r.status === 404) {
            // Job no longer in progress, check final status
            const fullJob = await apiFetch(`/api/jobs/${jobId}`)
            if (fullJob.ok) {
              const j = await fullJob.json()
              updateJobProgress(j)
              checkJobCompletion(j.status)
            }
          }
        } catch (e) {
          console.error('Polling error:', e)
        }
      }, POLLING_INTERVAL_MS)
    }

    const connectWebSocket = () => {
      try {
        ws = new WebSocket(wsUrl)
        
        ws.onopen = () => {
          console.log(`WebSocket connected for job ${jobId}`)
          reconnectAttempts = 0
          if (pollingTimer) {
            clearInterval(pollingTimer)
            pollingTimer = null
          }
        }

        ws.onmessage = (event) => {
          try {
            const p = JSON.parse(event.data)
            updateJobProgress(p)
            checkJobCompletion(p.status)
          } catch (e) {
            console.error(e)
          }
        }

        ws.onclose = () => {
          if (!shouldReconnect || activeJobIdRef.current !== jobId) {
            return
          }
          
          // Check if job is still running before reconnecting
          apiFetch(`/api/jobs/${jobId}/progress`)
            .then((r) => r.ok ? r.json() : null)
            .then((p) => {
              if (p && (p.status === 'processing' || p.status === 'pending')) {
                // Job still running, attempt reconnect
                if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                  reconnectAttempts++
                  const backoffMs = calculateBackoff(reconnectAttempts)
                  console.log(`WebSocket closed, reconnecting in ${backoffMs}ms (attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`)
                  reconnectTimer = setTimeout(connectWebSocket, backoffMs)
                } else {
                  console.log(`Max reconnection attempts reached, falling back to polling`)
                  startPolling()
                }
              } else {
                // Job completed or not found, fetch final state
                fetchJobs()
              }
            })
            .catch(() => {
              // Error fetching progress, try reconnecting or polling
              if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                reconnectAttempts++
                const backoffMs = calculateBackoff(reconnectAttempts)
                reconnectTimer = setTimeout(connectWebSocket, backoffMs)
              } else {
                startPolling()
              }
            })
        }

        ws.onerror = () => {
          console.error('WebSocket error')
        }
      } catch (e) {
        console.error('WebSocket creation error:', e)
        // Fall back to polling immediately
        startPolling()
      }
    }

    connectWebSocket()

    return () => {
      shouldReconnect = false
      clearTimeout(reconnectTimer)
      clearInterval(pollingTimer)
      if (ws && ws.readyState !== WebSocket.CLOSED) ws.close()
    }
  }, [activeJobId, projectId])

  const fetchVersion = async () => {
    try {
      const r = await apiFetch('/api/version')
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
      const r = await apiFetch(`/api/projects/${projectId}`)
      if (!r.ok) throw new Error('Project not found')
      setProject(await r.json())
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const TERMINAL_JOB_STATUSES = ['completed', 'failed', 'cancelled']

  const fetchJobs = async () => {
    try {
      const r = await apiFetch(`/api/projects/${projectId}/jobs`)
      if (!r.ok) return
      const jobList = await r.json()
      setJobs(jobList)
      // If the page was refreshed while a job was running, restore activeJobId so websocket/polling reconnects
      const runningJob = jobList.find((j) => j.status && !TERMINAL_JOB_STATUSES.includes(j.status))
      if (runningJob) {
        setActiveJobId(runningJob.job_id)
      }
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
        apiFetch('/api/settings'),
        project?.set_num ? apiFetch(`/api/sets/${encodeURIComponent(project.set_num)}/parts`) : Promise.resolve(null)
      ])
      if (settingsRes?.ok) {
        const s = await settingsRes.json()
        setWizardGlobalSettings(s)
        setPlateWidth(s.default_plate_width ?? 220)
        setPlateDepth(s.default_plate_depth ?? 220)
        setPlateHeight(s.default_plate_height ?? 250)
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
      const r = await apiFetch(`/api/projects/${projectId}/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plate_width: plateWidth,
          plate_depth: plateDepth,
          plate_height: plateHeight,
          generate_3mf: format3mf,
          generate_stl: formatStl,
          bypass_cache: bypassCache,
          per_part_rotation: Object.keys(perPartRotation).length ? perPartRotation : undefined,
          scale_factor: (scaleFactor != null && scaleFactor > 0) ? Number(scaleFactor) : (parseFloat(wizardGlobalSettings?.stl_scale_factor) || 1.0)
        })
      })
      if (!r.ok) return
      const data = await r.json()
      const jobId = data.job_id
      setWizardOpen(false)
      setCreatingJob(false)
      setJobs(prev => {
        const exists = prev.some(j => j.job_id === jobId)
        if (exists) return prev
        const now = new Date().toISOString()
        return [{ job_id: jobId, set_num: project?.set_num ?? '', status: 'pending', progress: 0, error_message: null, output_file: null, brickgen_version: data.brickgen_version ?? null, log: null, created_at: now, updated_at: now }, ...prev]
      })
      setActiveJobId(jobId)
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
      const r = await apiFetch(`/api/jobs/${jobId}/rerun`, { method: 'POST' })
      if (!r.ok) return
      const data = await r.json()
      setActiveJobId(data.job_id ?? null)
      await fetchJobs()
    } catch (e) {
      console.error(e)
    }
  }

  const downloadJobFile = async (jobId) => {
    try {
      const r = await apiFetch(`/api/download/${jobId}`)
      if (!r.ok) return
      
      // Get the filename from Content-Disposition header or use a default
      const contentDisposition = r.headers.get('Content-Disposition')
      let filename = 'download.zip'
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+?)"?$/i)
        if (filenameMatch) filename = filenameMatch[1]
      }
      
      const blob = await r.blob()
      
      // Use File System Access API if available (prompts user for save location)
      if (window.showSaveFilePicker) {
        try {
          const fileExtension = filename.split('.').pop()
          const handle = await window.showSaveFilePicker({
            suggestedName: filename,
            types: [{
              description: fileExtension === 'zip' ? 'ZIP Archive' : '3MF File',
              accept: fileExtension === 'zip' 
                ? { 'application/zip': ['.zip'] }
                : { 'application/vnd.ms-package.3dmanufacturing-3dmodel+xml': ['.3mf'] }
            }]
          })
          const writable = await handle.createWritable()
          await writable.write(blob)
          await writable.close()
          return
        } catch (err) {
          // User cancelled the save dialog or browser blocked it
          if (err.name !== 'AbortError') {
            console.error('Save picker failed:', err)
          }
          return
        }
      }
      
      // Fallback: programmatic download (browser may or may not prompt based on settings)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (e) {
      console.error('Download failed:', e)
    }
  }

  const deleteJobFiles = async (jobId) => {
    if (!confirm('Remove this job\'s output file from disk?')) return
    try {
      const r = await apiFetch(`/api/jobs/${jobId}/files`, { method: 'DELETE' })
      if (!r.ok) return
      await fetchJobs()
    } catch (e) {
      console.error(e)
    }
  }

  const cancelJob = async (jobId) => {
    if (!confirm('Cancel this job? The slot will be freed and the job marked as cancelled.')) return
    setCancellingJobId(jobId)
    try {
      const r = await apiFetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' })
      if (!r.ok) return
      setJobs((prev) =>
        prev.map((job) =>
          job.job_id === jobId
            ? { ...job, status: 'cancelled', error_message: 'Cancelled by user' }
            : job
        )
      )
      setActiveJobId((prev) => (prev === jobId ? null : prev))
    } catch (e) {
      console.error(e)
    } finally {
      setCancellingJobId(null)
    }
  }

  const deleteJob = async (jobId) => {
    if (!confirm('Delete this job and its output file? This cannot be undone.')) return
    setDeletingJobId(jobId)
    try {
      const r = await apiFetch(`/api/jobs/${jobId}`, { method: 'DELETE' })
      if (!r.ok) return
      await fetchJobs()
    } catch (e) {
      console.error(e)
    } finally {
      setDeletingJobId(null)
    }
  }

  const deleteProject = async () => {
    if (!confirm('Delete this project and all its jobs and output files?')) return
    try {
      const r = await apiFetch(`/api/projects/${projectId}`, { method: 'DELETE' })
      if (!r.ok) return
      navigate('/projects')
    } catch (e) {
      console.error(e)
    }
  }

  if (loading || !project) return <LoadingState />

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
          <div className="mt-4">
            <DataTable
              columns={[
                {
                  key: 'preview',
                  label: 'Preview',
                  className: 'w-20',
                  render: (p) => (
                    <img
                      src={`/api/parts/preview/${encodeURIComponent(p.ldraw_id || p.part_num)}?size=128${p.color_rgb ? `&color=${encodeURIComponent(p.color_rgb)}` : ''}`}
                      alt=""
                      className="w-12 h-12 object-contain bg-dk-1 rounded"
                      onError={(e) => { e.target.style.display = 'none' }}
                    />
                  )
                },
                { key: 'part_identifier', label: 'Part', className: 'font-mono', render: (p) => p.ldraw_id || p.part_num },
                { key: 'name', label: 'Name', className: 'truncate max-w-[200px]' },
                { key: 'quantity', label: 'Qty' },
                { key: 'color', label: 'Color' }
              ]}
              data={partsToShow}
              getRowKey={(p, i) => (partsPage - 1) * PARTS_PAGE_SIZE + i}
              emptyMessage="No parts found."
            />
            {partsTotalPages > 1 && (
              <div className="mt-2 pt-2 border-t border-dk-3">
                <Pagination
                  page={partsPage}
                  totalPages={partsTotalPages}
                  onPageChange={setPartsPage}
                  totalCount={partsList.length}
                />
              </div>
            )}
          </div>
        </details>
      )}

      {partColorRefList.length > 0 && (
        <details className="bg-dk-2 rounded-lg border border-dk-3 p-4 mb-6">
          <summary className="cursor-pointer font-semibold text-dk-5 hover:text-mint">Part &amp; color reference (for Bambu Studio / OrcaSlicer)</summary>
          <p className="mt-2 mb-3 text-sm text-dk-5/90">Use this list to assign filament to parts in your slicer. Part number format is <code className="bg-dk-1 px-1 rounded">LDrawId_instance</code> (e.g. 3404_1, 3404_2).</p>
          <div>
            <DataTable
              columns={[
                { key: 'partId', label: 'Part number', className: 'font-mono' },
                { key: 'color', label: 'Color' },
                { key: 'color_rgb', label: 'Hex code', className: 'font-mono', render: (row) => row.color_rgb !== '—' ? `#${row.color_rgb}` : row.color_rgb }
              ]}
              data={colorRefToShow}
              getRowKey={(row) => row.partId}
              emptyMessage="No color reference data."
            />
            {colorRefTotalPages > 1 && (
              <div className="mt-2 pt-2 border-t border-dk-3">
                <Pagination
                  page={colorRefPage}
                  totalPages={colorRefTotalPages}
                  onPageChange={setColorRefPage}
                  totalCount={partColorRefList.length}
                />
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
          <EmptyState message='No jobs yet. Click "New job" to create one (wizard will guide you through settings).' />
        ) : (
          <DataTable
            columns={[
              {
                key: 'job_id',
                label: 'Job ID',
                render: (j) => (
                  <div className="flex items-center gap-2 flex-wrap">
                    <code className="text-sm font-mono text-dk-5 bg-dk-1 px-2 py-0.5 rounded border border-dk-3" title={j.job_id}>
                      {j.job_id.slice(0, 8)}…
                    </code>
                    <Badge 
                      variant={
                        j.status === 'completed' ? 'success' : 
                        j.status === 'failed' ? 'danger' : 
                        j.status === 'cancelled' ? 'warning' : 
                        'default'
                      }
                    >
                      {j.status}
                    </Badge>
                    {j.brickgen_version && currentVersion && j.brickgen_version !== currentVersion && (
                      <span className="text-amber-400 text-xs">(different version)</span>
                    )}
                  </div>
                )
              },
              {
                key: 'created_at',
                label: 'Details',
                render: (j) => (
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-0.5 text-xs text-dk-5/80">
                    <span>Created {new Date(j.created_at).toLocaleString()}</span>
                    {j.brickgen_version && <span>BrickGen {j.brickgen_version}</span>}
                  </div>
                )
              }
            ]}
            data={jobs}
            getRowKey={(j) => j.job_id}
            rowActions={(j) => (
              <>
                {j.status === 'completed' && j.output_file && (
                  <button onClick={() => downloadJobFile(j.job_id)} className="px-3 py-1 bg-mint text-dk-1 rounded text-sm hover:opacity-90">Download</button>
                )}
                {TERMINAL_JOB_STATUSES.includes(j.status) && (
                  <button onClick={() => rerunJob(j.job_id, j.brickgen_version)} className="px-3 py-1 border border-dk-3 rounded text-sm text-dk-5 hover:bg-dk-3">Re-run</button>
                )}
                {j.output_file && (
                  <button onClick={() => deleteJobFiles(j.job_id)} className="px-3 py-1 text-dk-5 border border-dk-3 rounded text-sm hover:bg-dk-3">Clear files</button>
                )}
                {!TERMINAL_JOB_STATUSES.includes(j.status) ? (
                  <button onClick={() => cancelJob(j.job_id)} disabled={cancellingJobId === j.job_id} className="px-3 py-1 text-amber-400 hover:text-amber-300 hover:bg-dk-3 rounded text-sm disabled:opacity-50">
                    {cancellingJobId === j.job_id ? 'Cancelling…' : 'Cancel job'}
                  </button>
                ) : (
                  <button onClick={() => deleteJob(j.job_id)} disabled={deletingJobId === j.job_id} className="px-3 py-1 text-danger hover:text-danger/80 hover:bg-dk-3 rounded text-sm disabled:opacity-50">
                    {deletingJobId === j.job_id ? 'Deleting…' : 'Delete job'}
                  </button>
                )}
              </>
            )}
            expandedContent={(j) => (
              <>
                {(j.status === 'processing' || j.status === 'pending') && j.progress !== undefined && (
                  <div className="mb-2">
                    <ProgressBar value={j.progress} label={`Progress: ${j.progress}%`} />
                    {j.log && (
                      <p className="mt-1.5 text-xs font-mono text-dk-5/90 truncate" title={j.log.trim()}>
                        {(() => {
                          const lines = j.log.trim().split(/\r?\n/).filter(Boolean)
                          return lines.length ? lines[lines.length - 1] : j.log.trim()
                        })()}
                      </p>
                    )}
                  </div>
                )}
                {j.status === 'failed' && j.error_message && (
                  <p className="mb-2 text-sm text-danger">Error: {j.error_message}</p>
                )}
                {(j.log || j.status === 'completed' || j.status === 'failed') && (
                  <details>
                    <summary className="text-sm text-dk-5 cursor-pointer hover:text-mint">Job log</summary>
                    <pre className="mt-1 p-2 bg-dk-1 rounded text-xs text-left overflow-x-auto whitespace-pre-wrap font-mono text-dk-5">{j.log || 'No log entries.'}</pre>
                  </details>
                )}
              </>
            )}
          />
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
                </div>
              )}
              {wizardStep === 1 && (
                <div className="space-y-4">
                  <p className="text-sm text-dk-5">Set your build plate size (from global settings by default). Only used for 3MF output.</p>
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="block text-sm font-medium mb-1 text-dk-4">Plate width (mm)</label>
                      <input type="number" value={plateWidth} onChange={(e) => setPlateWidth(Number(e.target.value))} min={100} max={2000} className="w-full px-3 py-2 border border-dk-3 rounded bg-dk-1 text-dk-5" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1 text-dk-4">Plate depth (mm)</label>
                      <input type="number" value={plateDepth} onChange={(e) => setPlateDepth(Number(e.target.value))} min={100} max={2000} className="w-full px-3 py-2 border border-dk-3 rounded bg-dk-1 text-dk-5" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1 text-dk-4">Plate height (mm)</label>
                      <input type="number" value={plateHeight} onChange={(e) => setPlateHeight(Number(e.target.value))} min={100} max={2000} className="w-full px-3 py-2 border border-dk-3 rounded bg-dk-1 text-dk-5" />
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
                    <label className="block text-sm font-medium mb-1 text-dk-5">Current Job STL scale factor (optional)</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0.01"
                      max="10"
                      placeholder={wizardGlobalSettings ? `Default: ${formatScale(wizardGlobalSettings.stl_scale_factor)}` : 'Default: 1.0'}
                      value={scaleFactor ?? ''}
                      onChange={(e) => setScaleFactor(e.target.value === '' ? null : Number(e.target.value))}
                      className="w-full px-3 py-2 border border-dk-3 rounded bg-dk-1 text-dk-5"
                    />
                    <p className="text-xs text-dk-5/70 mt-1">Leave empty to use global default.</p>
                  </div>
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
                    <Pagination
                      page={wizardPartsPage}
                      totalPages={wizardPartsTotalPages}
                      onPageChange={setWizardPartsPage}
                      totalCount={wizardParts.length}
                    />
                  )}
                </div>
                )
              })()}
              {wizardStep === 4 && (
                <div className="space-y-3 text-sm text-dk-5">
                  {format3mf && <p><strong>Build plate:</strong> {plateWidth}mm x {plateDepth}mm x {plateHeight}mm</p>}
                  <p><strong>Output:</strong> {[format3mf && '3MF', formatStl && 'STL (in stls/)'].filter(Boolean).join(', ') || 'None'}</p>
                  <p><strong>Bypass cache:</strong> {bypassCache ? 'Yes' : 'No'}</p>
                  {Object.keys(perPartRotation).length > 0 && (
                    <p><strong>Per-part rotation:</strong> {Object.keys(perPartRotation).length} part(s) customized</p>
                  )}
                  {wizardGlobalSettings && (
                    <p><strong>Scale:</strong> {scaleFactor != null ? formatScale(scaleFactor) : `Default ${formatScale(wizardGlobalSettings?.stl_scale_factor)}`} · <strong>Global Rotation:</strong> {wizardGlobalSettings.rotation_enabled ? `X=${wizardGlobalSettings.rotation_x ?? 0}°, Y=${wizardGlobalSettings.rotation_y ?? 0}°, Z=${wizardGlobalSettings.rotation_z ?? 0}°` : 'Off'}</p>
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
