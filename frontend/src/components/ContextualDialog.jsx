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

  const updatePosition = () => {
    if (targetSelector && dialogRef.current) {
      const targetElement = document.querySelector(targetSelector)
      if (targetElement) {
        const targetRect = targetElement.getBoundingClientRect()
        const dialogElement = dialogRef.current
        const dialogRect = dialogElement.getBoundingClientRect()
        
        let top, left, right, bottom
        
        // Calculate position with viewport boundary checks
        switch (position) {
          case 'bottom':
            top = targetRect.bottom + 12
            left = Math.max(12, Math.min(targetRect.left, window.innerWidth - dialogRect.width - 12))
            // If would overflow bottom, position above instead
            if (top + dialogRect.height > window.innerHeight - 12) {
              bottom = window.innerHeight - targetRect.top + 12
              dialogElement.style.bottom = `${bottom}px`
              dialogElement.style.top = 'auto'
            } else {
              dialogElement.style.top = `${top}px`
              dialogElement.style.bottom = 'auto'
            }
            dialogElement.style.left = `${left}px`
            dialogElement.style.right = 'auto'
            break
            
          case 'right':
            top = Math.max(12, Math.min(targetRect.top, window.innerHeight - dialogRect.height - 12))
            left = targetRect.right + 12
            // If would overflow right, position left instead
            if (left + dialogRect.width > window.innerWidth - 12) {
              right = window.innerWidth - targetRect.left + 12
              dialogElement.style.right = `${right}px`
              dialogElement.style.left = 'auto'
            } else {
              dialogElement.style.left = `${left}px`
              dialogElement.style.right = 'auto'
            }
            dialogElement.style.top = `${top}px`
            dialogElement.style.bottom = 'auto'
            break
            
          case 'left':
            top = Math.max(12, Math.min(targetRect.top, window.innerHeight - dialogRect.height - 12))
            right = window.innerWidth - targetRect.left + 12
            dialogElement.style.top = `${top}px`
            dialogElement.style.right = `${right}px`
            dialogElement.style.left = 'auto'
            dialogElement.style.bottom = 'auto'
            break
            
          case 'top':
            bottom = window.innerHeight - targetRect.top + 12
            left = Math.max(12, Math.min(targetRect.left, window.innerWidth - dialogRect.width - 12))
            dialogElement.style.bottom = `${bottom}px`
            dialogElement.style.left = `${left}px`
            dialogElement.style.top = 'auto'
            dialogElement.style.right = 'auto'
            break
            
          default:
            // Keep default positioning (top-right)
            break
        }
      }
    }
  }

  useEffect(() => {
    updatePosition()
    
    // Update position on window resize and scroll
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)
    
    return () => {
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
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
