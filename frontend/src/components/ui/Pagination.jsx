/**
 * Reusable Pagination component with prev/next navigation, page display, and optional page size selector
 */
export default function Pagination({
  page,
  totalPages,
  onPageChange,
  totalCount,
  pageSize,
  pageSizeOptions = [10, 20, 50, 100],
  onPageSizeChange,
  disabled = false
}) {
  const handlePrev = () => {
    if (page > 1 && !disabled) {
      onPageChange(page - 1)
    }
  }
  
  const handleNext = () => {
    if (page < totalPages && !disabled) {
      onPageChange(page + 1)
    }
  }
  
  const handlePageSizeChange = (e) => {
    if (onPageSizeChange && !disabled) {
      onPageSizeChange(Number(e.target.value))
    }
  }
  
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="flex items-center gap-2">
        <button
          onClick={handlePrev}
          disabled={page <= 1 || disabled}
          className="px-3 py-1 border border-dk-3 rounded text-sm text-dk-5 disabled:opacity-50 hover:bg-dk-3 disabled:hover:bg-transparent transition"
        >
          Previous
        </button>
        <span className="text-sm text-dk-5">
          Page {page} of {totalPages}
          {totalCount !== undefined && ` (${totalCount} total)`}
        </span>
        <button
          onClick={handleNext}
          disabled={page >= totalPages || disabled}
          className="px-3 py-1 border border-dk-3 rounded text-sm text-dk-5 disabled:opacity-50 hover:bg-dk-3 disabled:hover:bg-transparent transition"
        >
          Next
        </button>
      </div>
      
      {onPageSizeChange && pageSize && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-dk-5">Items per page:</span>
          <select
            value={pageSize}
            onChange={handlePageSizeChange}
            disabled={disabled}
            className="border border-dk-3 rounded px-2 py-1 bg-dk-1 text-dk-5 text-sm disabled:opacity-50"
          >
            {pageSizeOptions.map(size => (
              <option key={size} value={size}>{size}</option>
            ))}
          </select>
        </div>
      )}
    </div>
  )
}
