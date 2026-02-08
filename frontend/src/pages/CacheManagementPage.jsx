import { useNavigate } from 'react-router-dom'
import CacheManagementContent from '../components/CacheManagementContent'

export default function CacheManagementPage() {
  const navigate = useNavigate()
  return (
    <div className="max-w-4xl mx-auto">
      <button onClick={() => navigate('/settings')} className="mb-4 px-4 py-2 bg-dk-3 text-dk-5 rounded hover:bg-mint hover:text-dk-1 transition">← Settings</button>
      <h1 className="text-2xl font-bold mb-2 text-dk-5">Cache management</h1>
      <p className="text-dk-5/80 mb-6">Manage STL, Rebrickable, part preview, LDraw, and search history. Use the links in Settings to jump to a specific section.</p>
      <CacheManagementContent />
    </div>
  )
}
