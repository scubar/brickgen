/**
 * Reusable Modal component with overlay, panel, title, and close button
 */
export default function Modal({ 
  open, 
  onClose, 
  title, 
  children, 
  maxWidth = 'max-w-2xl' 
}) {
  if (!open) return null
  
  return (
    <div 
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" 
      onClick={onClose}
    >
      <div 
        className={`bg-dk-2 border border-dk-3 rounded-lg shadow-xl ${maxWidth} w-full max-h-[90vh] overflow-hidden flex flex-col`}
        onClick={e => e.stopPropagation()}
      >
        {title && (
          <div className="p-4 border-b border-dk-3 flex items-center justify-between">
            <h3 className="text-xl font-bold text-dk-5">{title}</h3>
            <button 
              type="button" 
              onClick={onClose} 
              className="text-dk-5 hover:text-mint text-2xl leading-none" 
              aria-label="Close"
            >
              ×
            </button>
          </div>
        )}
        <div className="p-4 overflow-auto flex-1 text-dk-5">
          {children}
        </div>
      </div>
    </div>
  )
}
