/**
 * Reusable DataTable component with declarative column configuration
 * 
 * @param {Array} columns - Array of column definitions: { key, label, className?, render? }
 * @param {Array} data - Array of data objects to display
 * @param {Function} getRowKey - Function to extract unique key from row (default: (row, index) => row.id || index)
 * @param {String} emptyMessage - Message to display when data is empty
 * @param {Boolean} loading - Show loading spinner when true
 * @param {Function} rowActions - Function that returns action elements for each row: (row) => <>{actions}</>
 * @param {Function} expandedContent - Function that returns expanded content for each row: (row) => <>{content}</>
 */
import LoadingSpinner from './LoadingSpinner'

export default function DataTable({ 
  columns, 
  data, 
  getRowKey = (row, index) => row.id || index,
  emptyMessage = 'No data available',
  loading = false,
  rowActions,
  expandedContent
}) {
  if (loading) {
    return (
      <div className="text-center py-8 text-dk-5">
        <LoadingSpinner size="lg" className="mx-auto" />
        <p className="mt-3">Loading...</p>
      </div>
    )
  }
  
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-8 text-dk-5">
        {emptyMessage}
      </div>
    )
  }
  
  // Add actions column if rowActions is provided
  const columnsWithActions = rowActions 
    ? [...columns, { key: '_actions', label: 'Actions', className: 'text-right' }]
    : columns
  
  const colSpan = columnsWithActions.length
  
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-dk-3">
        <thead className="bg-dk-1">
          <tr>
            {columnsWithActions.map((column, index) => (
              <th
                key={column.key || index}
                className={`px-4 py-3 text-left text-xs font-medium text-dk-5 uppercase tracking-wider ${column.className || ''}`}
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-dk-3">
          {data.map((row, index) => (
            <>
              <tr key={getRowKey(row, index)} className="hover:bg-dk-3/50 transition">
                {columns.map((column, colIndex) => (
                  <td
                    key={column.key || colIndex}
                    className={`px-4 py-3 text-sm text-dk-5 ${column.className || ''}`}
                  >
                    {column.render ? column.render(row) : row[column.key]}
                  </td>
                ))}
                {rowActions && (
                  <td className="px-4 py-3 text-sm text-right">
                    <div className="flex items-center justify-end gap-2">
                      {rowActions(row)}
                    </div>
                  </td>
                )}
              </tr>
              {expandedContent && expandedContent(row) && (
                <tr key={`${getRowKey(row, index)}-expanded`}>
                  <td colSpan={colSpan} className="px-4 py-3 bg-dk-1/30">
                    {expandedContent(row)}
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  )
}
