import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]

function SearchPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [count, setCount] = useState(0)
  const [nextPage, setNextPage] = useState(null)
  const [prevPage, setPrevPage] = useState(null)
  const [searchHistory, setSearchHistory] = useState([])
  const [suggestions, setSuggestions] = useState([])
  const [showSuggest, setShowSuggest] = useState(false)
  const suggestRef = useRef(null)

  useEffect(() => {
    fetchHistory()
  }, [])

  useEffect(() => {
    const state = location.state
    if (state?.searchQuery != null && state.searchQuery.trim()) {
      setQuery(state.searchQuery)
      setPage(state.searchPage ?? 1)
      setPageSize(state.pageSize ?? 20)
      setLoading(true)
      setError(null)
      const pageNum = state.searchPage ?? 1
      const size = state.pageSize ?? 20
      fetch(`/api/search?query=${encodeURIComponent(state.searchQuery)}&page=${pageNum}&page_size=${size}`)
        .then((r) => r.ok ? r.json() : Promise.reject(new Error('Search failed')))
        .then((data) => {
          setResults(data.results || [])
          setCount(data.count ?? 0)
          setNextPage(data.next ?? null)
          setPrevPage(data.previous ?? null)
          setPage(data.page ?? pageNum)
          setPageSize(data.page_size ?? size)
        })
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false))
    }
  }, [location.state])

  useEffect(() => {
    if (!query.trim()) {
      setSuggestions([])
      return
    }
    const t = setTimeout(() => {
      fetch(`/api/search/suggest?q=${encodeURIComponent(query)}&limit=10`)
        .then((r) => r.ok ? r.json() : [])
        .then(setSuggestions)
        .catch(() => setSuggestions([]))
    }, 200)
    return () => clearTimeout(t)
  }, [query])

  useEffect(() => {
    const onBlur = () => setTimeout(() => setShowSuggest(false), 150)
    suggestRef.current?.addEventListener('blur', onBlur)
    return () => suggestRef.current?.removeEventListener('blur', onBlur)
  }, [])

  const fetchHistory = async () => {
    try {
      const r = await fetch('/api/search/history?limit=20')
      if (r.ok) setSearchHistory(await r.json())
    } catch (e) {
      console.error(e)
    }
  }

  const handleSearch = async (e, pageNum = 1) => {
    if (e) e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const url = `/api/search?query=${encodeURIComponent(query)}&page=${pageNum}&page_size=${pageSize}`
      const response = await fetch(url)
      if (!response.ok) throw new Error('Search failed')
      const data = await response.json()
      setResults(data.results || [])
      setCount(data.count ?? 0)
      setNextPage(data.next ?? null)
      setPrevPage(data.previous ?? null)
      setPage(data.page ?? pageNum)
      setPageSize(data.page_size ?? pageSize)
      setShowSuggest(false)
      fetchHistory()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const removeHistoryItem = async (q) => {
    try {
      const r = await fetch(`/api/search/history?query=${encodeURIComponent(q)}`, { method: 'DELETE' })
      if (r.ok) setSearchHistory((prev) => prev.filter((x) => x !== q))
    } catch (e) {
      console.error(e)
    }
  }

  const pickSuggestion = (item) => {
    setQuery(item.set_num)
    setShowSuggest(false)
    setSuggestions([])
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-dk-2 border border-dk-3 rounded-lg p-6 mb-8">
        <h2 className="text-2xl font-bold mb-4 text-dk-5">Search LEGO Sets</h2>
        <form onSubmit={(e) => handleSearch(e, 1)} className="flex gap-2 relative" ref={suggestRef}>
          <div className="flex-1 relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => query && setShowSuggest(true)}
              placeholder="Enter set name or number..."
              className="w-full px-4 py-2 border border-dk-3 rounded-lg bg-dk-1 text-dk-5 placeholder-dk-4/60 focus:outline-none focus:ring-2 focus:ring-mint"
            />
            {showSuggest && suggestions.length > 0 && (
              <ul className="absolute z-10 top-full left-0 right-0 mt-1 bg-dk-2 border border-dk-3 rounded-lg shadow-lg max-h-60 overflow-auto">
                {suggestions.map((s) => (
                  <li key={s.set_num} className="px-4 py-2 hover:bg-dk-3 cursor-pointer border-b border-dk-3 last:border-0 text-dk-5" onMouseDown={() => pickSuggestion(s)}>
                    <span className="font-medium">{s.set_num}</span>
                    <span className="ml-2 opacity-90">{s.name}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 bg-mint text-dk-1 rounded-lg hover:opacity-90 disabled:opacity-50 transition"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>

        {searchHistory.length > 0 && (
          <div className="mt-4">
            <p className="text-sm font-medium text-dk-5 mb-2">Recent searches</p>
            <div className="flex flex-wrap gap-2">
              {searchHistory.map((q) => (
                <span key={q} className="inline-flex items-center gap-1 px-3 py-1 bg-dk-3 rounded-full text-sm text-dk-5">
                  <button type="button" onClick={() => setQuery(q)} className="hover:text-mint">{q}</button>
                  <button type="button" onClick={() => removeHistoryItem(q)} className="hover:text-danger font-bold" aria-label="Remove">×</button>
                </span>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4 p-3 bg-danger/20 text-danger rounded">
            Error: {error}
          </div>
        )}
      </div>

      {results.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {results.map((set) => (
              <div
                key={set.set_num}
                onClick={() => navigate(`/set/${set.set_num}`, { state: { searchQuery: query, searchPage: page, pageSize } })}
                className="bg-dk-2 border border-dk-3 rounded-lg overflow-hidden cursor-pointer hover:border-mint/50 transition"
              >
                {set.image_url && <img src={set.image_url} alt={set.name} className="w-full h-48 object-contain bg-dk-1 p-4" />}
                <div className="p-4">
                  <h3 className="font-bold text-lg mb-1 text-dk-5">{set.name}</h3>
                  <p className="text-sm text-dk-5/80 mb-2">Set #{set.set_num}</p>
                  {set.year && <p className="text-sm text-dk-5/70">Year: {set.year}</p>}
                  {set.pieces && <p className="text-sm text-dk-5/70">Pieces: {set.pieces}</p>}
                  {set.theme && <p className="text-sm text-dk-5/70">Theme: {set.theme}</p>}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-4 text-dk-5">
            <div className="flex items-center gap-2 text-sm">
              <span>Items per page:</span>
              <select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); handleSearch(null, 1) }} className="border border-dk-3 rounded px-2 py-1 bg-dk-1 text-dk-5">
                {PAGE_SIZE_OPTIONS.map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
            {(nextPage != null || prevPage != null) && (
              <div className="flex items-center gap-2">
                <button type="button" disabled={prevPage == null} onClick={() => handleSearch(null, prevPage)} className="px-4 py-2 border border-dk-3 rounded disabled:opacity-50 hover:bg-dk-3 text-dk-5">Previous</button>
                <span className="text-sm">Page {page} of {Math.max(1, Math.ceil(count / pageSize))} ({count} total)</span>
                <button type="button" disabled={nextPage == null} onClick={() => handleSearch(null, nextPage)} className="px-4 py-2 border border-dk-3 rounded disabled:opacity-50 hover:bg-dk-3 text-dk-5">Next</button>
              </div>
            )}
          </div>
        </>
      )}

      {!loading && results.length === 0 && query && (
        <div className="text-center text-dk-5 py-8">
          No results found. Try a different search term.
        </div>
      )}
    </div>
  )
}

export default SearchPage
