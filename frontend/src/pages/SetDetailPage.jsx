import { useState, useEffect } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'

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

  const PARTS_PAGE_SIZE = 20
  const partsTotalPages = Math.max(1, Math.ceil(partsList.length / PARTS_PAGE_SIZE))
  const partsToShow = partsList.slice((partsPage - 1) * PARTS_PAGE_SIZE, partsPage * PARTS_PAGE_SIZE)

  useEffect(() => {
    fetchSetDetail()
    fetchPartsList()
  }, [setNum])
  useEffect(() => setPartsPage(1), [setNum, partsList.length])

  useEffect(() => {
    fetch('/api/settings')
      .then(r => r.ok ? r.json() : {})
      .then(s => setAutoGeneratePartPreviews(s.auto_generate_part_previews !== false))
      .catch(() => {})
  }, [])

  const fetchSetDetail = async () => {
    try {
      const response = await fetch(`/api/sets/${setNum}`)
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
      const response = await fetch(`/api/sets/${setNum}/parts`)
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
      const r = await fetch('/api/projects', {
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

  if (loading) {
    return <div className="text-center py-8 text-dk-5">Loading...</div>
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

                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-dk-3">
                      <thead className="bg-dk-1">
                        <tr>
                          {autoGeneratePartPreviews && <th className="px-2 py-3 text-left text-xs font-medium text-dk-5 uppercase tracking-wider w-24">Preview</th>}
                          <th className="px-4 py-3 text-left text-xs font-medium text-dk-5 uppercase tracking-wider">Part #</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-dk-5 uppercase tracking-wider">Name</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-dk-5 uppercase tracking-wider">Qty</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-dk-5 uppercase tracking-wider">Color</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-dk-5 uppercase tracking-wider">Links</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-dk-3">
                        {partsToShow.map((part, index) => (
                          <tr key={(partsPage - 1) * PARTS_PAGE_SIZE + index} className="hover:bg-dk-3/50 text-dk-5">
                            {autoGeneratePartPreviews && (
                              <td className="px-2 py-2">
                                <button type="button" onClick={() => setExpandedPreview(part)} className="block focus:outline-none focus:ring-2 focus:ring-mint rounded">
                                  <img
                                    src={`/api/parts/preview/${encodeURIComponent(part.ldraw_id || part.part_num)}?size=256${part.color_rgb ? `&color=${encodeURIComponent(part.color_rgb)}` : ''}`}
                                    alt=""
                                    className="w-20 h-20 object-contain bg-dk-1 rounded hover:opacity-90"
                                    onError={(e) => { e.target.style.display = 'none' }}
                                  />
                                </button>
                              </td>
                            )}
                            <td className="px-4 py-3 whitespace-nowrap text-sm font-mono">
                              {part.part_num}
                            </td>
                            <td className="px-4 py-3 text-sm text-dk-5">
                              {part.name}
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-dk-5">
                              {part.quantity}
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm">
                              <div className="flex items-center gap-2">
                                {part.color_rgb && (
                                  <span
                                    style={{ backgroundColor: '#' + part.color_rgb }}
                                    className="w-5 h-5 inline-block border border-dk-3 rounded"
                                    title={part.color}
                                  ></span>
                                )}
                                <span className="text-dk-5">{part.color}</span>
                              </div>
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm">
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
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {partsList.length > PARTS_PAGE_SIZE && (
                    <div className="flex items-center justify-between mt-4">
                      <span className="text-sm text-dk-5">
                        Page {partsPage} of {partsTotalPages} ({partsList.length} parts)
                      </span>
                      <div className="flex gap-2">
                        <button type="button" onClick={() => setPartsPage(p => Math.max(1, p - 1))} disabled={partsPage <= 1} className="px-3 py-1 border rounded text-sm disabled:opacity-50">Previous</button>
                        <button type="button" onClick={() => setPartsPage(p => Math.min(partsTotalPages, p + 1))} disabled={partsPage >= partsTotalPages} className="px-3 py-1 border rounded text-sm disabled:opacity-50">Next</button>
                      </div>
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
