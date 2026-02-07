import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

function SetDetailPage() {
  const { setNum } = useParams()
  const navigate = useNavigate()
  const [setDetail, setSetDetail] = useState(null)
  const [partsList, setPartsList] = useState([])
  const [showParts, setShowParts] = useState(false)
  const [loadingParts, setLoadingParts] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [plateWidth, setPlateWidth] = useState(220)
  const [plateDepth, setPlateDepth] = useState(220)
  const [bypassCache, setBypassCache] = useState(false)
  const [outputFormat, setOutputFormat] = useState('3mf')  // '3mf' or 'zip'
  const [generating, setGenerating] = useState(false)
  const [jobId, setJobId] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)

  useEffect(() => {
    fetchSetDetail()
    fetchSettings()
    fetchPartsList()
  }, [setNum])

  useEffect(() => {
    if (jobId && jobStatus?.status !== 'completed' && jobStatus?.status !== 'failed') {
      const interval = setInterval(() => {
        checkJobStatus()
      }, 2000)
      return () => clearInterval(interval)
    }
  }, [jobId, jobStatus])

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

  const fetchSettings = async () => {
    try {
      const response = await fetch('/api/settings')
      if (response.ok) {
        const data = await response.json()
        setPlateWidth(data.default_plate_width)
        setPlateDepth(data.default_plate_depth)
      }
    } catch (err) {
      console.error('Failed to fetch settings:', err)
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

  const handleGenerate = async () => {
    setGenerating(true)
    setError(null)

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          set_num: setNum,
          plate_width: plateWidth,
          plate_depth: plateDepth,
          bypass_cache: bypassCache,
          generate_3mf: outputFormat === '3mf',
        }),
      })

      if (!response.ok) throw new Error('Failed to start generation')

      const job = await response.json()
      setJobId(job.job_id)
      setJobStatus(job)
    } catch (err) {
      setError(err.message)
      setGenerating(false)
    }
  }

  const checkJobStatus = async () => {
    if (!jobId) return

    try {
      const response = await fetch(`/api/jobs/${jobId}`)
      if (!response.ok) return

      const status = await response.json()
      setJobStatus(status)

      if (status.status === 'completed' || status.status === 'failed') {
        setGenerating(false)
      }
    } catch (err) {
      console.error('Failed to check job status:', err)
    }
  }

  const handleDownload = () => {
    if (jobId && jobStatus?.status === 'completed') {
      window.location.href = `/api/download/${jobId}`
    }
  }

  if (loading) {
    return <div className="text-center py-8">Loading...</div>
  }

  if (error && !setDetail) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-red-100 text-red-700 p-4 rounded">
          Error: {error}
        </div>
        <button
          onClick={() => navigate('/')}
          className="mt-4 px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
        >
          Back to Search
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <button
        onClick={() => navigate('/')}
        className="mb-4 px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
      >
        ← Back to Search
      </button>

      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
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
            <h1 className="text-3xl font-bold mb-2">{setDetail.name}</h1>
            <p className="text-lg text-gray-600 mb-4">Set #{setDetail.set_num}</p>
            
            <div className="space-y-2 text-gray-700">
              {setDetail.year && <p>Year: {setDetail.year}</p>}
              {setDetail.theme && <p>Theme: {setDetail.theme}</p>}
              {setDetail.subtheme && <p>Subtheme: {setDetail.subtheme}</p>}
              {setDetail.pieces && <p>Pieces: {setDetail.pieces}</p>}
              {setDetail.parts_count && <p>Unique Parts: {setDetail.parts_count}</p>}
            </div>
          </div>
        </div>

        {/* Parts List Section - Now integrated with set details */}
        <div className="border-t border-gray-200 pt-6">
          <button
            onClick={() => setShowParts(!showParts)}
            className="w-full flex items-center justify-between text-left mb-4"
          >
            <h2 className="text-2xl font-bold">
              Parts List ({partsList.length} unique parts)
            </h2>
            <span className="text-2xl">{showParts ? '▼' : '▶'}</span>
          </button>

          {showParts && (
            <div>
              {loadingParts ? (
                <div className="text-center py-4">Loading parts...</div>
              ) : partsList.length > 0 ? (
                <>
                  <div className="mb-4">
                    <a
                      href={`https://rebrickable.com/sets/${setNum}/`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
                    >
                      View Full Set on Rebrickable →
                    </a>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Part #
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Name
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Qty
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Color
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Links
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {partsList.map((part, index) => (
                          <tr key={index} className="hover:bg-gray-50">
                            <td className="px-4 py-3 whitespace-nowrap text-sm font-mono">
                              {part.part_num}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-900">
                              {part.name}
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                              {part.quantity}
                            </td>
                            <td className="px-4 py-3 whitespace-nowrap text-sm">
                              <div className="flex items-center gap-2">
                                {part.color_rgb && (
                                  <span
                                    style={{ backgroundColor: '#' + part.color_rgb }}
                                    className="w-5 h-5 inline-block border border-gray-300 rounded"
                                    title={part.color}
                                  ></span>
                                )}
                                <span className="text-gray-700">{part.color}</span>
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
                                    <span className="text-gray-400">|</span>
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
                </>
              ) : (
                <div className="text-center py-4 text-gray-500">No parts data available</div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Generate Files Section - Now at bottom */}
        <h2 className="text-2xl font-bold mb-4">Generate Files</h2>
        
        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-sm font-medium mb-2">
              Output Format
            </label>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="outputFormat"
                  value="3mf"
                  checked={outputFormat === '3mf'}
                  onChange={(e) => setOutputFormat(e.target.value)}
                  className="w-4 h-4 text-red-600 border-gray-300 focus:ring-red-500"
                />
                <span className="ml-2 text-sm">
                  <strong>3MF file</strong> - Parts pre-arranged on build plate (recommended)
                </span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="outputFormat"
                  value="zip"
                  checked={outputFormat === 'zip'}
                  onChange={(e) => setOutputFormat(e.target.value)}
                  className="w-4 h-4 text-red-600 border-gray-300 focus:ring-red-500"
                />
                <span className="ml-2 text-sm">
                  <strong>ZIP file</strong> - Individual STL files for manual arrangement
                </span>
              </label>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Build Plate Width (mm)
              </label>
                <input
                  type="number"
                  value={plateWidth}
                  onChange={(e) => setPlateWidth(parseInt(e.target.value))}
                  min="100"
                  max="2000"
                  className="w-full px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
                />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                Build Plate Depth (mm)
              </label>
                <input
                  type="number"
                  value={plateDepth}
                  onChange={(e) => setPlateDepth(parseInt(e.target.value))}
                  min="100"
                  max="2000"
                  className="w-full px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-red-500"
                />
            </div>
          </div>
          
          <div className="flex items-center">
            <input
              type="checkbox"
              id="bypassCache"
              checked={bypassCache}
              onChange={(e) => setBypassCache(e.target.checked)}
              className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
            />
            <label htmlFor="bypassCache" className="ml-2 text-sm font-medium">
              Bypass cache (reconvert all parts)
            </label>
          </div>
          
          <div className="bg-blue-50 border border-blue-200 rounded p-3">
            <p className="text-sm text-blue-800">
              💡 <strong>Tip:</strong> Auto-orientation and scaling can be adjusted in{' '}
              <button 
                onClick={() => navigate('/settings')}
                className="underline hover:text-blue-900"
              >
                Settings
              </button>
              . These settings are applied globally to all generations.
            </p>
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={generating}
          className="w-full px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-400 transition font-semibold"
        >
          {generating ? 'Generating...' : `Generate ${outputFormat.toUpperCase()} File`}
        </button>

        {jobStatus && (
          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="font-semibold">Status:</span>
              <span className={`px-3 py-1 rounded text-sm font-medium ${
                jobStatus.status === 'completed' ? 'bg-green-100 text-green-800' :
                jobStatus.status === 'failed' ? 'bg-red-100 text-red-800' :
                jobStatus.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {jobStatus.status}
              </span>
            </div>
            
            {jobStatus.status !== 'failed' && (
              <div className="mb-2">
                <div className="flex items-center justify-between text-sm mb-1">
                  <span>Progress</span>
                  <span>{jobStatus.progress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-red-600 h-2 rounded-full transition-all"
                    style={{ width: `${jobStatus.progress}%` }}
                  />
                </div>
              </div>
            )}

            {jobStatus.error_message && (
              <div className="text-red-600 text-sm mt-2">
                Error: {jobStatus.error_message}
              </div>
            )}

            {jobStatus.status === 'completed' && (
              <div className="mt-4 space-y-2">
                <button
                  onClick={handleDownload}
                  className="w-full px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition font-semibold"
                >
                  Download {jobStatus.output_file?.endsWith('.3mf') ? '3MF' : 'ZIP'} File
                </button>
                <p className="text-sm text-gray-500 text-center">
                  {jobStatus.output_file?.endsWith('.3mf') 
                    ? 'Import into your slicer - parts are already arranged on the build plate'
                    : 'Contains all individual STL files for each part'}
                </p>
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="mt-4 p-3 bg-red-100 text-red-700 rounded">
            Error: {error}
          </div>
        )}
      </div>
  )
}

export default SetDetailPage
