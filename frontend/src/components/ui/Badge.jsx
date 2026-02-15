/**
 * Reusable Badge component for status indicators and labels
 */
export default function Badge({ variant = 'default', children, className = '' }) {
  const baseClasses = 'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded'
  
  const variantClasses = {
    success: 'bg-mint/20 text-mint border border-mint/40',
    danger: 'bg-danger/20 text-danger border border-danger/40',
    warning: 'bg-amber-500/20 text-amber-200 border border-amber-500/40',
    default: 'bg-dk-3 text-dk-5 border border-dk-3'
  }
  
  return (
    <span className={`${baseClasses} ${variantClasses[variant]} ${className}`}>
      {children}
    </span>
  )
}
