/**
 * Reusable LoadingSpinner component for inline loading states
 */
export default function LoadingSpinner({ size = 'md', className = '' }) {
  const sizeClasses = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-2',
    lg: 'w-12 h-12 border-3'
  }
  
  return (
    <div className={`inline-block ${sizeClasses[size]} border-dk-3 border-t-mint rounded-full animate-spin ${className}`}></div>
  )
}
