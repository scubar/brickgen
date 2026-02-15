import { useEffect, useRef } from 'react'

/**
 * ContextualDialog - A floating dialog box that appears near target elements
 * Used for non-blocking guidance and tooltips
 */
function ContextualDialog({ 
  position = 'top-right',
  targetSelector = null,
  onDismiss,
  showDismiss = true,
  children,
  className = ''
}) {
  const dialogRef = useRef(null)

  useEffect(() => {
    if (targetSelector && dialogRef.current) {
      const targetElement = document.querySelector(targetSelector)
      if (targetElement) {
        const targetRect = targetElement.getBoundingClientRect()
        const dialogElement = dialogRef.current
        
        // Position dialog based on target element and position preference
        switch (position) {
          case 'bottom':
            dialogElement.style.top = `${targetRect.bottom + 12}px`
            dialogElement.style.left = `${targetRect.left}px`
            break
          case 'right':
            dialogElement.style.top = `${targetRect.top}px`
            dialogElement.style.left = `${targetRect.right + 12}px`
            break
          case 'left':
            dialogElement.style.top = `${targetRect.top}px`
            dialogElement.style.right = `${window.innerWidth - targetRect.left + 12}px`
            break
          case 'top':
            dialogElement.style.bottom = `${window.innerHeight - targetRect.top + 12}px`
            dialogElement.style.left = `${targetRect.left}px`
            break
          default:
            // Keep default positioning
            break
        }
      }
    }
  }, [targetSelector, position])

  const getArrowClasses = () => {
    switch (position) {
      case 'bottom':
        return 'absolute -top-2 left-6 w-4 h-4 bg-dk-2 border-l border-t border-dk-3 transform rotate-45'
      case 'right':
        return 'absolute -left-2 top-6 w-4 h-4 bg-dk-2 border-l border-b border-dk-3 transform rotate-45'
      case 'left':
        return 'absolute -right-2 top-6 w-4 h-4 bg-dk-2 border-r border-t border-dk-3 transform rotate-45'
      case 'top':
        return 'absolute -bottom-2 left-6 w-4 h-4 bg-dk-2 border-r border-b border-dk-3 transform rotate-45'
      default:
        return ''
    }
  }

  const baseClasses = targetSelector 
    ? 'fixed z-[60]'
    : 'fixed top-20 right-4 z-[60]'

  return (
    <div 
      ref={dialogRef}
      className={`${baseClasses} ${className}`}
    >
      <div className="relative bg-dk-2 rounded-lg shadow-2xl border border-dk-3 max-w-md">
        {targetSelector && position && position !== 'top-right' && (
          <div className={getArrowClasses()} />
        )}
        
        {showDismiss && onDismiss && (
          <button
            onClick={onDismiss}
            className="absolute top-2 right-2 text-dk-5/60 hover:text-dk-5 transition"
            title="Close wizard"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
        
        <div className="p-4">
          {children}
        </div>
      </div>
    </div>
  )
}

export default ContextualDialog
