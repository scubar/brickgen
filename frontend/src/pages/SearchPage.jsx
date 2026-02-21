import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { apiFetch } from '../api'
import { Pagination, LoadingState, EmptyState } from '../components/ui'

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
  const [cachedSets, setCachedSets] = useState([])
  const [projects, setProjects] = useState([])
  const [loadingCached, setLoadingCached] = useState(true)
  const [loadingProjects, setLoadingProjects] = useState(true)

  useEffect(() => {
    fetchHistory()
  }, [])

  const fetchCachedSets = async () => {
    setLoadingCached(true)
    try {
      const r = await apiFetch('/api/cache/rebrickable/random?limit=4')
      if (r.ok) setCachedSets(await r.json())
    } catch (e) {
      console.error(e)
    } finally {
      setLoadingCached(false)
    }
  }

  const fetchProjects = async () => {
    setLoadingProjects(true)
    try {
      const r = await apiFetch('/api/projects')
      if (r.ok) setProjects(await r.json())
    } catch (e) {
      console.error(e)
    } finally {
      setLoadingProjects(false)
    }
  }

  useEffect(() => {
    fetchCachedSets()
    fetchProjects()
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
      apiFetch(`/api/search?query=${encodeURIComponent(state.searchQuery)}&page=${pageNum}&page_size=${size}`)
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
      apiFetch(`/api/search/suggest?q=${encodeURIComponent(query)}&limit=10`)
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
      const r = await apiFetch('/api/search/history?limit=20')
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
      const response = await apiFetch(url)
      if (!response.ok) throw new Error('Search failed')
      const data = await response.json()
      setResults(data.results || [])
      setCount(data.count ?? 0)
      setNextPage(data.next ?? null)
      setPrevPage(data.previous ?? null)
      setPage(data.page ?? pageNum)
      setPageSize(data.page_size ?? pageSize)
      window.dispatchEvent(new CustomEvent('onboarding:search-run', {
        detail: {
          query,
          count: data.count ?? 0,
          page: data.page ?? pageNum,
          pageSize: data.page_size ?? pageSize,
        },
      }))
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
      const r = await apiFetch(`/api/search/history?query=${encodeURIComponent(q)}`, { method: 'DELETE' })
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
        <h2 className="text-2xl font-bold mb-4 text-dk-5">Search sets</h2>
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
          <div className="bg-dk-2 border border-dk-3 rounded-lg p-6 mb-8">
            <h2 className="text-xl font-bold mb-4 text-dk-5">Search results</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {results.map((set) => (
                <div
                  key={set.set_num}
                  onClick={() => navigate(`/set/${set.set_num}`, { state: { searchQuery: query, searchPage: page, pageSize } })}
                  className="bg-dk-1 border border-dk-3 rounded-lg overflow-hidden cursor-pointer hover:border-mint/50 transition"
                >
                  {set.image_url && <img src={set.image_url} alt={set.name} className="w-full h-36 object-contain bg-dk-2 p-3" />}
                  <div className="p-3">
                    <h3 className="font-bold text-sm mb-1 text-dk-5 truncate" title={set.name}>{set.name}</h3>
                    <p className="text-xs text-dk-5/80">Set #{set.set_num}</p>
                    {(set.year != null || set.pieces != null) && (
                      <p className="text-xs text-dk-5/70 mt-1">
                        {[set.year != null && `Year: ${set.year}`, set.pieces != null && `${set.pieces} pcs`].filter(Boolean).join(' · ')}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap items-center justify-center gap-4 text-dk-5 text-sm">
              {(nextPage != null || prevPage != null) && (
                <Pagination
                  page={page}
                  totalPages={Math.max(1, Math.ceil(count / pageSize))}
                  onPageChange={(newPage) => {
                    if (newPage > page && nextPage != null) {
                      handleSearch(null, nextPage)
                    } else if (newPage < page && prevPage != null) {
                      handleSearch(null, prevPage)
                    }
                  }}
                  totalCount={count}
                  pageSize={pageSize}
                  pageSizeOptions={PAGE_SIZE_OPTIONS}
                  onPageSizeChange={(newSize) => { 
                    setPageSize(newSize)
                    handleSearch(null, 1)
                  }}
                />
              )}
            </div>
          </div>
        </>
      )}

      {(loadingProjects || projects.length > 0) && (
        <div className="bg-dk-2 border border-dk-3 rounded-lg p-6 mb-8">
          <h2 className="text-xl font-bold mb-4 text-dk-5">Recent Projects</h2>
          {loadingProjects ? (
            <LoadingState message="Loading projects…" />
          ) : projects.length === 0 ? (
            <EmptyState message="No projects yet. Open a set and create a project to get started." />
          ) : (
            <div className="grid gap-3">
              {projects.slice(0, 3).map((p) => (
                <div
                  key={p.id}
                  onClick={() => navigate(`/projects/${p.id}`)}
                  className="bg-dk-1 border border-dk-3 rounded-lg p-3 flex items-center justify-between cursor-pointer hover:border-mint/50 transition"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    {p.image_url && (
                      <img src={p.image_url} alt="" className="w-12 h-12 object-contain bg-dk-2 rounded flex-shrink-0" />
                    )}
                    <div className="min-w-0">
                      <h3 className="font-semibold text-dk-5 truncate">{p.name}</h3>
                      <p className="text-xs text-dk-5/80">{p.set_num}{p.set_name ? ` · ${p.set_name}` : ''}</p>
                    </div>
                  </div>
                  <span className="text-mint flex-shrink-0">→</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {(loadingCached || cachedSets.length > 0) && results.length === 0 && (
        <div className="bg-dk-2 border border-dk-3 rounded-lg p-6 mb-8">
          <div className="flex items-center justify-between gap-4 mb-4">
            <h2 className="text-xl font-bold text-dk-5">Cached Sets (Random)</h2>
            <button
              type="button"
              onClick={fetchCachedSets}
              disabled={loadingCached}
              className="px-3 py-1.5 text-sm border border-dk-3 rounded-lg bg-dk-1 text-dk-5 hover:bg-dk-3 hover:border-dk-4 transition disabled:opacity-50"
              title="Refresh cached sets"
            >
              {loadingCached ? 'Refreshing…' : 'Refresh'}
            </button>
          </div>
          {loadingCached ? (
            <LoadingState message="Loading cached sets…" />
          ) : cachedSets.length === 0 ? (
            <EmptyState message="No cached sets yet. Search for a set to cache it." />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {cachedSets.map((set) => (
                <div
                  key={set.set_num}
                  onClick={() => navigate(`/set/${set.set_num}`)}
                  className="bg-dk-1 border border-dk-3 rounded-lg overflow-hidden cursor-pointer hover:border-mint/50 transition"
                >
                  {set.image_url && <img src={set.image_url} alt={set.name} className="w-full h-36 object-contain bg-dk-2 p-3" />}
                  <div className="p-3 relative">
                    <span className="absolute top-2 right-2 px-2 py-0.5 text-xs font-medium bg-mint/20 text-mint rounded border border-mint/40">Cached</span>
                    <h3 className="font-bold text-sm mb-1 text-dk-5 pr-16 truncate" title={set.name}>{set.name}</h3>
                    <p className="text-xs text-dk-5/80">Set #{set.set_num}</p>
                    {(set.year != null || set.pieces != null) && (
                      <p className="text-xs text-dk-5/70 mt-1">
                        {[set.year != null && `Year: ${set.year}`, set.pieces != null && `${set.pieces} pcs`].filter(Boolean).join(' · ')}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
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
