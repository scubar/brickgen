import { useNavigate } from 'react-router-dom'

function AttributionsPage() {
  const navigate = useNavigate()
  const items = [
    { name: 'LDraw', url: 'https://www.ldraw.org/', description: 'LEGO part library and format' },
    { name: 'LDView', url: 'https://github.com/tcobbs/ldview', description: 'LDraw viewer and STL export' },
    { name: 'Rebrickable API', url: 'https://rebrickable.com/api/', description: 'LEGO set and parts data' },
    { name: 'FastAPI', url: 'https://fastapi.tiangolo.com/', description: 'Backend API framework' },
    { name: 'React', url: 'https://react.dev/', description: 'Frontend UI library' },
    { name: 'Vite', url: 'https://vitejs.dev/', description: 'Frontend build tool' },
  ]

  return (
    <div className="max-w-2xl mx-auto">
      <button onClick={() => navigate(-1)} className="mb-4 px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700">← Back</button>
      <h1 className="text-2xl font-bold mb-6">Attributions</h1>
      <p className="text-gray-600 mb-6">This product uses the following third-party software and services.</p>
      <ul className="space-y-4">
        {items.map((item) => (
          <li key={item.name} className="bg-white rounded-lg shadow p-4">
            <a href={item.url} target="_blank" rel="noopener noreferrer" className="font-semibold text-blue-600 hover:underline">
              {item.name}
            </a>
            <p className="text-sm text-gray-600 mt-1">{item.description}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default AttributionsPage
