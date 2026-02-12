/**
 * Reusable DataTable component with declarative column configuration
 * 
 * @param {Array} columns - Array of column definitions: { key, label, className?, render? }
 * @param {Array} data - Array of data objects to display
 * @param {Function} getRowKey - Function to extract unique key from row (default: (row, index) => row.id || index)
 * @param {String} emptyMessage - Message to display when data is empty
 */
export default function DataTable({ 
  columns, 
  data, 
  getRowKey = (row, index) => row.id || index,
  emptyMessage = 'No data available'
}) {
  if (!data || data.length === 0) {
    return (
      <div className="text-center py-8 text-dk-5">
        {emptyMessage}
      </div>
    )
  }
  
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-dk-3">
        <thead className="bg-dk-1">
          <tr>
            {columns.map((column, index) => (
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
            <tr key={getRowKey(row, index)} className="hover:bg-dk-3/50 transition">
              {columns.map((column, index) => (
                <td
                  key={column.key || index}
                  className={`px-4 py-3 text-sm text-dk-5 ${column.className || ''}`}
                >
                  {column.render ? column.render(row) : row[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
