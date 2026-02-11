import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../api'

function ProjectsPage() {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetchProjects()
  }, [])

  const fetchProjects = async () => {
    try {
      const r = await apiFetch('/api/projects')
      if (r.ok) setProjects(await r.json())
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const deleteProject = async (e, projectId) => {
    e.stopPropagation()
    if (!confirm('Delete this project and all its jobs and output files?')) return
    setDeletingId(projectId)
    try {
      const r = await apiFetch(`/api/projects/${projectId}`, { method: 'DELETE' })
      if (r.ok) await fetchProjects()
    } catch (e) {
      console.error(e)
    } finally {
      setDeletingId(null)
    }
  }

  if (loading) return <div className="text-center py-8 text-dk-5">Loading...</div>

  return (
    <div className="max-w-4xl mx-auto">
      <button
        onClick={() => navigate('/')}
        className="mb-4 px-4 py-2 bg-dk-3 text-dk-5 rounded hover:bg-mint hover:text-dk-1 transition"
      >
        ← Back to Search
      </button>
      <h1 className="text-2xl font-bold mb-6 text-dk-5">Projects</h1>
      {projects.length === 0 ? (
        <p className="text-dk-5">No projects yet. Create one from a set detail page.</p>
      ) : (
        <div className="grid gap-4">
          {projects.map((p) => (
            <div
              key={p.id}
              className="bg-dk-2 rounded-lg border border-dk-3 p-4 flex items-center justify-between cursor-pointer hover:border-mint/50 transition"
              onClick={() => navigate(`/projects/${p.id}`)}
            >
              <div className="flex items-center gap-4">
                {p.image_url && (
                  <img src={p.image_url} alt="" className="w-16 h-16 object-contain bg-dk-1 rounded" />
                )}
                <div>
                  <h2 className="font-semibold text-dk-5">{p.name}</h2>
                  <p className="text-sm text-dk-5/80">{p.set_num} {p.set_name && ` · ${p.set_name}`}</p>
                </div>
              </div>
              <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                <span className="text-mint">→</span>
                <button
                  type="button"
                  onClick={(e) => deleteProject(e, p.id)}
                  disabled={deletingId === p.id}
                  className="px-3 py-1 text-danger hover:text-danger/80 hover:bg-dk-3 rounded text-sm disabled:opacity-50"
                  title="Delete project"
                >
                  {deletingId === p.id ? 'Deleting…' : 'Delete'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ProjectsPage
