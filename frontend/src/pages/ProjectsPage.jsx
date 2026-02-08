import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

function ProjectsPage() {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    fetchProjects()
  }, [])

  const fetchProjects = async () => {
    try {
      const r = await fetch('/api/projects')
      if (r.ok) setProjects(await r.json())
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="text-center py-8">Loading...</div>

  return (
    <div className="max-w-4xl mx-auto">
      <button
        onClick={() => navigate('/')}
        className="mb-4 px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
      >
        ← Back to Search
      </button>
      <h1 className="text-2xl font-bold mb-6">Projects</h1>
      {projects.length === 0 ? (
        <p className="text-gray-500">No projects yet. Create one from a set detail page.</p>
      ) : (
        <div className="grid gap-4">
          {projects.map((p) => (
            <div
              key={p.id}
              className="bg-white rounded-lg shadow p-4 flex items-center justify-between cursor-pointer hover:shadow-md"
              onClick={() => navigate(`/projects/${p.id}`)}
            >
              <div className="flex items-center gap-4">
                {p.image_url && (
                  <img src={p.image_url} alt="" className="w-16 h-16 object-contain bg-gray-50 rounded" />
                )}
                <div>
                  <h2 className="font-semibold">{p.name}</h2>
                  <p className="text-sm text-gray-600">{p.set_num} {p.set_name && ` · ${p.set_name}`}</p>
                </div>
              </div>
              <span className="text-gray-400">→</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ProjectsPage
