import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

function SearchPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const handleSearch = async (e) => {
    e.preventDefault()
    
    if (!query.trim()) {
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/search?query=${encodeURIComponent(query)}`)
      
      if (!response.ok) {
        throw new Error('Search failed')
      }

      const data = await response.json()
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-md p-6 mb-8">
        <h2 className="text-2xl font-bold mb-4">Search LEGO Sets</h2>
        
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter set name or number..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-400 transition"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>

        {error && (
          <div className="mt-4 p-3 bg-red-100 text-red-700 rounded">
            Error: {error}
          </div>
        )}
      </div>

      {results.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {results.map((set) => (
            <div
              key={set.set_num}
              onClick={() => navigate(`/set/${set.set_num}`)}
              className="bg-white rounded-lg shadow-md overflow-hidden cursor-pointer hover:shadow-lg transition"
            >
              {set.image_url && (
                <img
                  src={set.image_url}
                  alt={set.name}
                  className="w-full h-48 object-contain bg-gray-50 p-4"
                />
              )}
              <div className="p-4">
                <h3 className="font-bold text-lg mb-1">{set.name}</h3>
                <p className="text-sm text-gray-600 mb-2">Set #{set.set_num}</p>
                {set.year && <p className="text-sm text-gray-500">Year: {set.year}</p>}
                {set.pieces && <p className="text-sm text-gray-500">Pieces: {set.pieces}</p>}
                {set.theme && <p className="text-sm text-gray-500">Theme: {set.theme}</p>}
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && results.length === 0 && query && (
        <div className="text-center text-gray-500 py-8">
          No results found. Try a different search term.
        </div>
      )}
    </div>
  )
}

export default SearchPage
