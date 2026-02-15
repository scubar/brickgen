import { useState, useEffect } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { apiFetch } from '../api'
import { Pagination, DataTable, LoadingState, EmptyState } from '../components/ui'

function SetDetailPage() {
  const { setNum } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const backToSearch = () => navigate('/', { state: location.state || {} })
  const [setDetail, setSetDetail] = useState(null)
  const [partsList, setPartsList] = useState([])
  const [showParts, setShowParts] = useState(false)
  const [loadingParts, setLoadingParts] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [projectName, setProjectName] = useState('')
  const [creatingProject, setCreatingProject] = useState(false)
  const [projectDuplicateWarning, setProjectDuplicateWarning] = useState(false)
  const [autoGeneratePartPreviews, setAutoGeneratePartPreviews] = useState(true)
  const [partsPage, setPartsPage] = useState(1)
  const [expandedPreview, setExpandedPreview] = useState(null)
  const [projectsForSet, setProjectsForSet] = useState([])
  const [loadingProjects, setLoadingProjects] = useState(true)
  const [deletingProjectId, setDeletingProjectId] = useState(null)

  const PARTS_PAGE_SIZE = 5

  function sameSetNum(setNumFromUrl, projectSetNum) {
    if (!setNumFromUrl || !projectSetNum) return false
    if (setNumFromUrl === projectSetNum) return true
    if (setNumFromUrl.endsWith('-1') && setNumFromUrl.slice(0, -2) === projectSetNum) return true
    if (projectSetNum.endsWith('-1') && projectSetNum.slice(0, -2) === setNumFromUrl) return true
    if (setNumFromUrl + '-1' === projectSetNum) return true
    return false
  }
  const partsTotalPages = Math.max(1, Math.ceil(partsList.length / PARTS_PAGE_SIZE))
  const partsToShow = partsList.slice((partsPage - 1) * PARTS_PAGE_SIZE, partsPage * PARTS_PAGE_SIZE)

  useEffect(() => {
    fetchSetDetail()
    fetchPartsList()
  }, [setNum])
  useEffect(() => setPartsPage(1), [setNum, partsList.length])

  useEffect(() => {
    let cancelled = false
    setLoadingProjects(true)
    apiFetch('/api/projects')
      .then(r => r.ok ? r.json() : [])
      .then(all => {
        if (!cancelled && setNum) {
          setProjectsForSet(all.filter(p => sameSetNum(setNum, p.set_num)))
        }
      })
      .catch(() => { if (!cancelled) setProjectsForSet([]) })
      .finally(() => { if (!cancelled) setLoadingProjects(false) })
    return () => { cancelled = true }
  }, [setNum])

  useEffect(() => {
    apiFetch('/api/settings')
      .then(r => r.ok ? r.json() : {})
      .then(s => setAutoGeneratePartPreviews(s.auto_generate_part_previews !== false))
      .catch(() => {})
  }, [])

  const fetchSetDetail = async () => {
    try {
      const response = await apiFetch(`/api/sets/${setNum}`)
      if (!response.ok) throw new Error('Failed to fetch set details')
      const data = await response.json()
      setSetDetail(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchPartsList = async () => {
    try {
      setLoadingParts(true)
      const response = await apiFetch(`/api/sets/${setNum}/parts`)
      if (response.ok) {
        const data = await response.json()
        setPartsList(data)
      }
    } catch (err) {
      console.error('Failed to fetch parts list:', err)
    } finally {
      setLoadingParts(false)
    }
  }

  const handleCreateProject = async () => {
    const name = (projectName || setDetail?.name || setNum || 'Project').trim()
    if (!name) return
    setCreatingProject(true)
    setProjectDuplicateWarning(false)
    try {
      const r = await apiFetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ set_num: setDetail?.set_num || setNum, name })
      })
      if (!r.ok) throw new Error('Failed to create project')
      const data = await r.json()
      if (data.existing_project_for_set) setProjectDuplicateWarning(true)
      navigate(`/projects/${data.id}`)
    } catch (e) {
      setError(e.message)
    } finally {
      setCreatingProject(false)
    }
  }

  const deleteProject = async (e, projectId) => {
    e.stopPropagation()
    if (!confirm('Delete this project and all its jobs and output files?')) return
    setDeletingProjectId(projectId)
    try {
      const r = await apiFetch(`/api/projects/${projectId}`, { method: 'DELETE' })
      if (r.ok) {
        setProjectsForSet(prev => prev.filter(p => p.id !== projectId))
      }
    } catch (e) {
      console.error(e)
    } finally {
      setDeletingProjectId(null)
    }
  }

  if (loading) {
    return <LoadingState />
  }

  if (error && !setDetail) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-danger/20 text-danger p-4 rounded">
          Error: {error}
        </div>
        <button onClick={backToSearch} className="mt-4 px-4 py-2 bg-mint text-dk-1 rounded hover:opacity-90">
          Back to Search
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <button onClick={backToSearch} className="mb-4 px-4 py-2 bg-dk-3 text-dk-5 rounded hover:bg-mint hover:text-dk-1 transition">
        ← Back to Search
      </button>

      <div className="bg-dk-2 border border-dk-3 rounded-lg p-6 mb-6">
        <div className="grid md:grid-cols-2 gap-6 mb-6">
          <div>
            {setDetail.image_url && (
              <img
                src={setDetail.image_url}
                alt={setDetail.name}
                className="w-full rounded-lg"
              />
            )}
          </div>
          <div>
            <h1 className="text-3xl font-bold mb-2 text-dk-5">{setDetail.name}</h1>
            <p className="text-lg text-dk-5/80 mb-4">Set #{setDetail.set_num}</p>
            {setDetail.cached_at && (
              <p className="text-sm text-dk-5/70 mb-2">Data cached: {new Date(setDetail.cached_at).toLocaleString()}</p>
            )}
            <div className="space-y-2 text-dk-5">
              {setDetail.year && <p>Year: {setDetail.year}</p>}
              {setDetail.theme && <p>Theme: {setDetail.theme}</p>}
              {setDetail.subtheme && <p>Subtheme: {setDetail.subtheme}</p>}
              {setDetail.pieces && <p>Pieces: {setDetail.pieces}</p>}
              {setDetail.parts_count && <p>Unique Parts: {setDetail.parts_count}</p>}
            </div>
            <div className="mt-4 pt-4 border-t border-dk-3">
              <p className="text-sm font-medium text-dk-5 mb-2">Create project (to generate set multiple times with jobs)</p>
              <div className="flex gap-2 items-center">
                <input type="text" value={projectName} onChange={(e) => setProjectName(e.target.value)} placeholder={setDetail.name || 'Project name'} className="flex-1 max-w-xs px-3 py-2 border border-dk-3 rounded bg-dk-1 text-dk-5" />
                <button onClick={handleCreateProject} disabled={creatingProject} className="px-4 py-2 bg-mint text-dk-1 rounded hover:opacity-90 disabled:opacity-50">Create project</button>
              </div>
              {projectDuplicateWarning && <p className="text-amber-400 text-sm mt-1">A project for this set already exists; you can still create another.</p>}
            </div>
          </div>
        </div>

        <div className="border-t border-dk-3 pt-6 mt-6">
          <h2 className="text-2xl font-bold mb-4 text-dk-5">Projects for this set</h2>
          {loadingProjects ? (
            <LoadingState message="Loading projects..." />
          ) : projectsForSet.length === 0 ? (
            <EmptyState message="No projects for this set yet. Create one above." />
          ) : (
            <div className="grid gap-4">
              {projectsForSet.map((p) => (
                <div
                  key={p.id}
                  className="bg-dk-1 rounded-lg border border-dk-3 p-4 flex items-center justify-between cursor-pointer hover:border-mint/50 transition"
                  onClick={() => navigate(`/projects/${p.id}`)}
                >
                  <div className="flex items-center gap-4">
                    {p.image_url && (
                      <img src={p.image_url} alt="" className="w-16 h-16 object-contain bg-dk-2 rounded" />
                    )}
                    <div>
                      <h3 className="font-semibold text-dk-5">{p.name}</h3>
                      <p className="text-sm text-dk-5/80">{p.set_num} {p.set_name && ` · ${p.set_name}`}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                    <span className="text-mint">→</span>
                    <button
                      type="button"
                      onClick={(e) => deleteProject(e, p.id)}
                      disabled={deletingProjectId === p.id}
                      className="px-3 py-1 text-danger hover:text-danger/80 hover:bg-dk-3 rounded text-sm disabled:opacity-50"
                      title="Delete project"
                    >
                      {deletingProjectId === p.id ? 'Deleting…' : 'Delete'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="border-t border-dk-3 pt-6">
          <button onClick={() => setShowParts(!showParts)} className="w-full flex items-center justify-between text-left mb-4 text-dk-5 hover:text-mint">
            <h2 className="text-2xl font-bold">Parts List ({partsList.length} parts)</h2>
            <span className="text-2xl">{showParts ? '▼' : '▶'}</span>
          </button>

          {showParts && (
            <div>
              {loadingParts ? (
                <div className="text-center py-4 text-dk-5">Loading parts...</div>
              ) : partsList.length > 0 ? (
                <>
                  <div className="mb-4">
                    <a href={`https://rebrickable.com/sets/${setNum}/`} target="_blank" rel="noopener noreferrer" className="inline-block px-4 py-2 bg-mint text-dk-1 rounded hover:opacity-90 transition">
                      View Full Set on Rebrickable →
                    </a>
                  </div>

                  <DataTable
                    columns={[
                      ...(autoGeneratePartPreviews ? [{
                        key: 'preview',
                        label: 'Preview',
                        className: 'w-24',
                        render: (part) => (
                          <button type="button" onClick={() => setExpandedPreview(part)} className="block focus:outline-none focus:ring-2 focus:ring-mint rounded">
                            <img
                              src={`/api/parts/preview/${encodeURIComponent(part.ldraw_id || part.part_num)}?size=256${part.color_rgb ? `&color=${encodeURIComponent(part.color_rgb)}` : ''}`}
                              alt=""
                              className="w-20 h-20 object-contain bg-dk-1 rounded hover:opacity-90"
                              onError={(e) => { e.target.style.display = 'none' }}
                            />
                          </button>
                        )
                      }] : []),
                      { key: 'part_num', label: 'Part #', className: 'whitespace-nowrap font-mono' },
                      { key: 'name', label: 'Name' },
                      { key: 'quantity', label: 'Qty', className: 'whitespace-nowrap' },
                      {
                        key: 'color',
                        label: 'Color',
                        className: 'whitespace-nowrap',
                        render: (part) => (
                          <div className="flex items-center gap-2">
                            {part.color_rgb && (
                              <span
                                style={{ backgroundColor: '#' + part.color_rgb }}
                                className="w-5 h-5 inline-block border border-dk-3 rounded"
                                title={part.color}
                              ></span>
                            )}
                            <span>{part.color}</span>
                          </div>
                        )
                      },
                      {
                        key: 'links',
                        label: 'Links',
                        className: 'whitespace-nowrap',
                        render: (part) => (
                          <div className="flex gap-2">
                            <a
                              href={`https://rebrickable.com/parts/${part.part_num}/`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:text-blue-800 underline"
                            >
                              Rebrickable
                            </a>
                            {part.ldraw_id && (
                              <>
                                <span className="text-dk-5/60">|</span>
                                <a
                                  href={`https://library.ldraw.org/parts/list?tableSearch=${part.ldraw_id}.dat`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-blue-600 hover:text-blue-800 underline"
                                >
                                  LDraw
                                </a>
                              </>
                            )}
                          </div>
                        )
                      }
                    ]}
                    data={partsToShow}
                    getRowKey={(part, index) => (partsPage - 1) * PARTS_PAGE_SIZE + index}
                    emptyMessage="No parts found."
                  />
                  {partsList.length > PARTS_PAGE_SIZE && (
                    <div className="mt-4">
                      <Pagination
                        page={partsPage}
                        totalPages={partsTotalPages}
                        onPageChange={setPartsPage}
                        totalCount={partsList.length}
                      />
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-4 text-dk-5">No parts data available</div>
              )}
            </div>
          )}
        </div>
      </div>

      {expandedPreview && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4" onClick={() => setExpandedPreview(null)}>
          <div className="bg-dk-2 border border-dk-3 rounded-lg shadow-xl p-4 max-w-full" onClick={e => e.stopPropagation()}>
            <p className="text-sm font-medium mb-2 text-dk-5">{expandedPreview.ldraw_id || expandedPreview.part_num} {expandedPreview.name}</p>
            <img
              src={`/api/parts/preview/${encodeURIComponent(expandedPreview.ldraw_id || expandedPreview.part_num)}?size=256${expandedPreview.color_rgb ? `&color=${encodeURIComponent(expandedPreview.color_rgb)}` : ''}`}
              alt=""
              className="w-64 h-64 object-contain bg-dk-1 rounded"
            />
            <button type="button" onClick={() => setExpandedPreview(null)} className="mt-2 w-full py-1 border border-dk-3 rounded text-sm text-dk-5 hover:bg-dk-3">Close</button>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-4 p-3 bg-danger/20 text-danger rounded">
          Error: {error}
        </div>
      )}
    </div>
  )
}

export default SetDetailPage
