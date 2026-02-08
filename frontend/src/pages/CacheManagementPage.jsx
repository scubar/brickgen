import { useNavigate } from 'react-router-dom'
import CacheManagementContent from '../components/CacheManagementContent'

export default function CacheManagementPage() {
  const navigate = useNavigate()
  return (
    <div className="max-w-4xl mx-auto">
      <button onClick={() => navigate('/settings')} className="mb-4 px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700">← Settings</button>
      <h1 className="text-2xl font-bold mb-2">Cache management</h1>
      <p className="text-gray-600 mb-6">Manage STL, Rebrickable, part preview, LDraw, and search history. Use the links in Settings to jump to a specific section.</p>
      <CacheManagementContent />
    </div>
  )
}
