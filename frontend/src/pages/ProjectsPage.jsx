import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../api'
import { LoadingState, EmptyState } from '../components/ui'
import Modal from '../components/ui/Modal'

function ProjectsPage() {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState(null)
  const [showCustomModal, setShowCustomModal] = useState(false)
  const [customName, setCustomName] = useState('')
  const [creating, setCreating] = useState(false)
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

  const createCustomProject = async (e) => {
    e.preventDefault()
    if (!customName.trim()) return
    setCreating(true)
    try {
      const r = await apiFetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: customName.trim(), is_custom: true }),
      })
      if (r.ok) {
        const project = await r.json()
        setShowCustomModal(false)
        setCustomName('')
        navigate(`/projects/${project.id}`)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setCreating(false)
    }
  }

  if (loading) return <LoadingState />

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-dk-3 text-dk-5 rounded hover:bg-mint hover:text-dk-1 transition"
          >
            ← Back to Search
          </button>
          <h1 className="text-2xl font-bold text-dk-5">Projects</h1>
        </div>
        <button
          onClick={() => setShowCustomModal(true)}
          className="px-4 py-2 bg-mint text-dk-1 rounded font-semibold hover:bg-mint/80 transition"
        >
          + Custom Project
        </button>
      </div>

      {projects.length === 0 ? (
        <EmptyState message="No projects yet. Create one from a set detail page or use + Custom Project." />
      ) : (
        <div className="grid gap-4">
          {projects.map((p) => (
            <div
              key={p.id}
              className="bg-dk-2 rounded-lg border border-dk-3 p-4 flex items-center justify-between cursor-pointer hover:border-mint/50 transition"
              onClick={() => navigate(`/projects/${p.id}`)}
            >
              <div className="flex items-center gap-4">
                {p.image_url ? (
                  <img src={p.image_url} alt="" className="w-16 h-16 object-contain bg-dk-1 rounded" />
                ) : p.is_custom ? (
                  <div className="w-16 h-16 flex items-center justify-center bg-dk-1 rounded text-2xl">🧱</div>
                ) : null}
                <div>
                  <h2 className="font-semibold text-dk-5">{p.name}</h2>
                  <p className="text-sm text-dk-5/80">
                    {p.is_custom
                      ? <span className="italic text-mint/80">Custom project</span>
                      : <>{p.set_num}{p.set_name && ` · ${p.set_name}`}</>
                    }
                  </p>
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

      {/* Custom project creation modal */}
      <Modal open={showCustomModal} onClose={() => { setShowCustomModal(false); setCustomName('') }} title="New Custom Project">
        <form onSubmit={createCustomProject} className="flex flex-col gap-4">
          <p className="text-dk-5/80 text-sm">
            Create a project with self-selected parts from the local LDraw library.
            You can search for and add parts after creating the project.
          </p>
          <div>
            <label className="block text-sm font-medium text-dk-5 mb-1">Project Name</label>
            <input
              type="text"
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              placeholder="e.g. My Space Build"
              className="w-full px-3 py-2 bg-dk-1 border border-dk-3 rounded text-dk-5 focus:outline-none focus:border-mint"
              autoFocus
              required
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => { setShowCustomModal(false); setCustomName('') }}
              className="px-4 py-2 bg-dk-3 text-dk-5 rounded hover:bg-dk-4 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={creating || !customName.trim()}
              className="px-4 py-2 bg-mint text-dk-1 rounded font-semibold hover:bg-mint/80 transition disabled:opacity-50"
            >
              {creating ? 'Creating…' : 'Create'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

export default ProjectsPage

