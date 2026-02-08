import { useState, useEffect } from 'react'
import CacheSection from './CacheSection'

const PAGE_SIZE_OPTIONS = [10, 20, 50, 100]
const PREVIEW_ITEMS_PER_PAGE = 24
const SEARCH_HISTORY_PER_PAGE = 20

/** Shared cache management sections (STL, Rebrickable, preview, LDraw, search history). Used in Settings Cache tab and on standalone cache page. */
export default function CacheManagementContent() {
  const [cacheStats, setCacheStats] = useState(null)
  const [clearingCache, setClearingCache] = useState(false)
  const [cachedSets, setCachedSets] = useState([])
  const [rebrickableCount, setRebrickableCount] = useState(0)
  const [rebrickablePage, setRebrickablePage] = useState(1)
  const [rebrickablePageSize, setRebrickablePageSize] = useState(20)
  const [rebrickableNext, setRebrickableNext] = useState(null)
  const [rebrickablePrev, setRebrickablePrev] = useState(null)
  const [clearingRebrickable, setClearingRebrickable] = useState(false)
  const [clearingPreviewCache, setClearingPreviewCache] = useState(false)
  const [previewList, setPreviewList] = useState([])
  const [previewPage, setPreviewPage] = useState(1)
  const [ldrawStats, setLdrawStats] = useState(null)
  const [clearingLdraw, setClearingLdraw] = useState(false)
  const [searchHistory, setSearchHistory] = useState([])
  const [searchHistoryPage, setSearchHistoryPage] = useState(1)
  const [clearingSearchHistory, setClearingSearchHistory] = useState(false)
  const [message, setMessage] = useState(null)

  const fetchCacheStats = async () => {
    try {
      const r = await fetch('/api/cache/stats')
      if (r.ok) setCacheStats(await r.json())
    } catch (e) { console.error(e) }
  }
  const fetchCachedSets = async (page = 1, pageSize = null) => {
    const size = pageSize ?? rebrickablePageSize
    try {
      const r = await fetch(`/api/cache/rebrickable?page=${page}&page_size=${size}`)
      if (r.ok) {
        const d = await r.json()
        setCachedSets(d.results)
        setRebrickableCount(d.count)
        setRebrickablePage(d.page)
        setRebrickableNext(d.next)
        setRebrickablePrev(d.previous)
        if (pageSize != null) setRebrickablePageSize(size)
      }
    } catch (e) { console.error(e) }
  }
  const fetchLdrawStats = async () => {
    try {
      const r = await fetch('/api/ldraw/stats')
      if (r.ok) setLdrawStats(await r.json())
    } catch (e) { console.error(e) }
  }
  const fetchPreviewList = async () => {
    try {
      const r = await fetch('/api/parts/preview-cache/list')
      if (r.ok) {
        const d = await r.json()
        setPreviewList(d.items || [])
      }
    } catch (e) { console.error(e) }
  }
  const fetchSearchHistory = async () => {
    try {
      const r = await fetch('/api/search/history?limit=100')
      if (r.ok) setSearchHistory(await r.json())
    } catch (e) { console.error(e) }
  }

  useEffect(() => {
    fetchCacheStats()
    fetchCachedSets(1)
    fetchLdrawStats()
    fetchPreviewList()
    fetchSearchHistory()
  }, [])

  const handleRebrickablePageSizeChange = (newSize) => {
    fetchCachedSets(1, newSize)
  }
  const goToRebrickablePage = (page) => {
    fetchCachedSets(page)
  }

  const handleClearRebrickable = async (setNum = null) => {
    const url = setNum ? `/api/cache/rebrickable?set_num=${encodeURIComponent(setNum)}` : '/api/cache/rebrickable'
    if (!confirm(setNum ? `Clear cache for set ${setNum}?` : 'Clear all Rebrickable cached sets?')) return
    setClearingRebrickable(true)
    setMessage(null)
    try {
      const r = await fetch(url, { method: 'DELETE' })
      const data = await r.json()
      setMessage({ type: 'success', text: data.message })
      await fetchCachedSets(1)
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setClearingRebrickable(false)
    }
  }

  return (
    <>
      {message && (
        <div className={`mb-4 p-3 rounded ${message.type === 'success' ? 'bg-mint/20 text-mint' : 'bg-danger/20 text-danger'}`}>
          {message.text}
        </div>
      )}
      <div className="space-y-6">
        <CacheSection id="stl-cache" title="STL cache" description="Converted LDraw parts cached as STL files. Clearing forces reconversion on next generation.">
          {cacheStats && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><p className="text-dk-5/80 font-medium">Cached files</p><p className="text-2xl font-bold text-dk-5">{cacheStats.stl_count}</p></div>
                <div><p className="text-dk-5/80 font-medium">Total size</p><p className="text-2xl font-bold text-dk-5">{cacheStats.total_size_mb.toFixed(2)} MB</p></div>
              </div>
              <p className="text-xs text-dk-5/80">Directory: {cacheStats.cache_dir}</p>
              <button onClick={async () => { if (!confirm('Clear all cached STL files?')) return; setClearingCache(true); try { const r = await fetch('/api/cache/clear', { method: 'DELETE' }); const d = await r.json(); setMessage({ type: 'success', text: d.message }); fetchCacheStats(); } catch (e) { setMessage({ type: 'error', text: e.message }); } finally { setClearingCache(false); } }} disabled={clearingCache} className="w-full px-4 py-2 bg-mint text-dk-1 rounded hover:opacity-90 disabled:opacity-50">{clearingCache ? 'Clearing...' : 'Clear STL cache'}</button>
            </div>
          )}
        </CacheSection>
        <CacheSection id="rebrickable-cache" title="Rebrickable cache" description="Cached set metadata and parts lists from Rebrickable. Clear to free space or refresh data.">
          <div className="space-y-4">
            {rebrickableCount > 0 && (
              <button onClick={() => handleClearRebrickable()} disabled={clearingRebrickable} className="w-full px-4 py-2 bg-mint text-dk-1 rounded hover:opacity-90 disabled:opacity-50">{clearingRebrickable ? 'Clearing...' : 'Clear all Rebrickable cache'}</button>
            )}
            {cachedSets.length === 0 ? <p className="text-dk-5/80">No cached sets.</p> : (
              <>
                <ul className="divide-y divide-dk-3 max-h-64 overflow-y-auto">
                  {cachedSets.map((c) => (
                    <li key={c.set_num} className="py-2 flex items-center gap-3">
                      {(c.image_url || c.set_num) && <img src={c.image_url || `https://img.bricklink.com/ItemImage/SN/0/${(c.set_num || '').replace('-1', '')}.png`} alt="" className="w-10 h-10 object-contain bg-dk-1 rounded" onError={(e) => { e.target.style.display = 'none' }} />}
                      <div className="flex-1 min-w-0"><span className="font-medium text-dk-5">{c.set_num}</span><span className="text-dk-5/80 ml-2 truncate block">{c.name}</span><p className="text-xs text-dk-5/80">Cached: {c.cached_at ? new Date(c.cached_at).toLocaleString() : '—'}</p></div>
                      <button type="button" onClick={() => handleClearRebrickable(c.set_num)} disabled={clearingRebrickable} className="text-dk-5 hover:text-mint hover:underline text-sm">Clear</button>
                    </li>
                  ))}
                </ul>
                <div className="flex flex-wrap items-center justify-between gap-2 pt-2">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-dk-5/80">Items per page:</span>
                    <select value={rebrickablePageSize} onChange={(e) => handleRebrickablePageSizeChange(Number(e.target.value))} className="border border-dk-3 rounded px-2 py-1 text-dk-5 bg-dk-1">{PAGE_SIZE_OPTIONS.map((n) => <option key={n} value={n}>{n}</option>)}</select>
                  </div>
                  {(rebrickablePrev !== null || rebrickableNext !== null) && (
                    <div className="flex items-center gap-2">
                      <button type="button" onClick={() => goToRebrickablePage(rebrickablePrev)} disabled={rebrickablePrev === null} className="px-2 py-1 border border-dk-3 rounded text-sm text-dk-5 disabled:opacity-50">Previous</button>
                      <span className="text-sm text-dk-5/80">Page {rebrickablePage} of {Math.max(1, Math.ceil(rebrickableCount / rebrickablePageSize))} ({rebrickableCount} total)</span>
                      <button type="button" onClick={() => goToRebrickablePage(rebrickableNext)} disabled={rebrickableNext === null} className="px-2 py-1 border border-dk-3 rounded text-sm text-dk-5 disabled:opacity-50">Next</button>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </CacheSection>
        <CacheSection id="preview-cache" title="Part preview cache" description="Cached part preview images (PNG). Cleared images are regenerated on next view.">
          <div className="space-y-4">
            {previewList.length > 0 && (() => {
              const totalPages = Math.max(1, Math.ceil(previewList.length / PREVIEW_ITEMS_PER_PAGE))
              const start = (previewPage - 1) * PREVIEW_ITEMS_PER_PAGE
              const pageItems = previewList.slice(start, start + PREVIEW_ITEMS_PER_PAGE)
              return (
                <>
                  <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2 max-h-64 overflow-y-auto">
                    {pageItems.map((item, idx) => {
                      const url = `/api/parts/preview/${encodeURIComponent(item.ldraw_id)}?size=128&rotation_x=${item.rotation_x || 0}&rotation_y=${item.rotation_y || 0}&rotation_z=${item.rotation_z || 0}`
                      return (<div key={`${item.ldraw_id}-${item.size}-${start + idx}`} className="flex flex-col items-center"><img src={url} alt="" className="w-14 h-14 object-contain bg-dk-1 rounded border border-dk-3" onError={(e) => { e.target.style.display = 'none' }} /><span className="text-xs truncate w-full text-center text-dk-5" title={item.ldraw_id}>{item.ldraw_id}</span></div>)
                    })}
                  </div>
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between gap-2 pt-2 border-t border-dk-3">
                      <button type="button" onClick={() => setPreviewPage((p) => Math.max(1, p - 1))} disabled={previewPage <= 1} className="px-2 py-1 border border-dk-3 rounded text-sm text-dk-5 disabled:opacity-50">Previous</button>
                      <span className="text-sm text-dk-5/80">Page {previewPage} of {totalPages} ({previewList.length} total)</span>
                      <button type="button" onClick={() => setPreviewPage((p) => Math.min(totalPages, p + 1))} disabled={previewPage >= totalPages} className="px-2 py-1 border border-dk-3 rounded text-sm text-dk-5 disabled:opacity-50">Next</button>
                    </div>
                  )}
                </>
              )
            })()}
            <p className="text-sm text-dk-5/80">{previewList.length} cached preview(s)</p>
            <button onClick={async () => { if (!confirm('Clear all part preview images?')) return; setClearingPreviewCache(true); setPreviewPage(1); try { const r = await fetch('/api/parts/preview-cache', { method: 'DELETE' }); const d = await r.json(); setMessage({ type: 'success', text: d.message }); fetchPreviewList(); } catch (e) { setMessage({ type: 'error', text: e.message }); } finally { setClearingPreviewCache(false); } }} disabled={clearingPreviewCache} className="w-full px-4 py-2 bg-mint text-dk-1 rounded hover:opacity-90 disabled:opacity-50">{clearingPreviewCache ? 'Clearing...' : 'Clear preview cache'}</button>
          </div>
        </CacheSection>
        <CacheSection id="ldraw-cache" title="LDraw library" description="LDraw parts library on disk. Clearing removes it; it will be re-downloaded on next generation." thumbnailAlt="LDraw">
          <div className="space-y-4">
            {ldrawStats && (
              <>
                <div className="flex items-center justify-between"><span className="text-sm text-dk-5/80 font-medium">Status</span><span className={`px-2 py-1 rounded text-sm font-medium ${ldrawStats.exists ? 'bg-mint/20 text-mint' : 'bg-danger/20 text-danger'}`}>{ldrawStats.exists ? 'Downloaded' : 'Not downloaded'}</span></div>
                {ldrawStats.exists && <div className="grid grid-cols-2 gap-4 text-sm"><div><p className="text-dk-5/80 font-medium">Part files</p><p className="text-xl font-bold text-dk-5">{ldrawStats.part_count?.toLocaleString() ?? '—'}</p></div><div><p className="text-dk-5/80 font-medium">Size</p><p className="text-xl font-bold text-dk-5">{ldrawStats.total_size_mb?.toFixed(2) ?? '—'} MB</p></div></div>}
                <p className="text-xs text-dk-5">Path: {ldrawStats.library_path}</p>
                <button onClick={async () => { if (!confirm('Clear LDraw library? It will be re-downloaded (~40MB) on next generation.')) return; setClearingLdraw(true); try { const r = await fetch('/api/ldraw/clear', { method: 'DELETE' }); const d = await r.json(); setMessage({ type: 'success', text: d.message }); fetchLdrawStats(); } catch (e) { setMessage({ type: 'error', text: e.message }); } finally { setClearingLdraw(false); } }} disabled={clearingLdraw || !ldrawStats?.exists} className="w-full px-4 py-2 bg-mint text-dk-1 rounded hover:opacity-90 disabled:opacity-50">{clearingLdraw ? 'Clearing...' : 'Clear LDraw library'}</button>
              </>
            )}
          </div>
        </CacheSection>
        <CacheSection id="search-history-cache" title="Search history" description="Recent search queries used for suggestions. Clearing removes all history.">
          <div className="space-y-4">
            {searchHistory.length > 0 ? (() => {
              const totalPages = Math.max(1, Math.ceil(searchHistory.length / SEARCH_HISTORY_PER_PAGE))
              const start = (searchHistoryPage - 1) * SEARCH_HISTORY_PER_PAGE
              const pageQueries = searchHistory.slice(start, start + SEARCH_HISTORY_PER_PAGE)
              return (
                <>
                  <ul className="divide-y divide-dk-3 max-h-48 overflow-y-auto">
                    {pageQueries.map((q) => <li key={q} className="py-2 text-sm font-mono text-dk-5">{q}</li>)}
                  </ul>
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between gap-2 pt-2 border-t border-dk-3">
                      <button type="button" onClick={() => setSearchHistoryPage((p) => Math.max(1, p - 1))} disabled={searchHistoryPage <= 1} className="px-2 py-1 border border-dk-3 rounded text-sm text-dk-5 disabled:opacity-50">Previous</button>
                      <span className="text-sm text-dk-5/80">Page {searchHistoryPage} of {totalPages} ({searchHistory.length} total)</span>
                      <button type="button" onClick={() => setSearchHistoryPage((p) => Math.min(totalPages, p + 1))} disabled={searchHistoryPage >= totalPages} className="px-2 py-1 border border-dk-3 rounded text-sm text-dk-5 disabled:opacity-50">Next</button>
                    </div>
                  )}
                  <p className="text-sm text-dk-5/80">{searchHistory.length} query(ies)</p>
                </>
              )
            })() : <p className="text-dk-5/80">No search history.</p>}
            <button onClick={async () => { if (!confirm('Clear all search history?')) return; setClearingSearchHistory(true); try { const r = await fetch('/api/search/history/clear', { method: 'DELETE' }); const d = await r.json(); setMessage({ type: 'success', text: d.message }); await fetchSearchHistory(); } catch (e) { setMessage({ type: 'error', text: e.message }); } finally { setClearingSearchHistory(false); setSearchHistoryPage(1); } }} disabled={clearingSearchHistory || searchHistory.length === 0} className="w-full px-4 py-2 bg-mint text-dk-1 rounded hover:opacity-90 disabled:opacity-50">{clearingSearchHistory ? 'Clearing...' : 'Clear all search history'}</button>
          </div>
        </CacheSection>
      </div>
    </>
  )
}
