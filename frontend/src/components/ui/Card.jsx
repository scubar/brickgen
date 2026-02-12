/**
 * Reusable Card component for consistent panel containers
 */
export default function Card({ title, children, actions, className = '' }) {
  return (
    <div className={`bg-dk-2 rounded-lg border border-dk-3 ${className}`}>
      {title && (
        <div className="p-4 border-b border-dk-3 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-dk-5">{title}</h3>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className="p-4">
        {children}
      </div>
    </div>
  )
}
