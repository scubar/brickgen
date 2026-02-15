/**
 * Reusable Button component with consistent styling for primary, secondary, danger, and ghost variants
 */
export default function Button({ 
  variant = 'primary', 
  size = 'md',
  disabled = false, 
  children, 
  ...rest 
}) {
  const baseClasses = 'rounded font-medium transition disabled:opacity-50 disabled:cursor-not-allowed'
  
  const variantClasses = {
    primary: 'bg-mint text-dk-1 hover:opacity-90',
    secondary: 'border border-dk-3 text-dk-5 hover:bg-dk-3',
    danger: 'text-danger hover:text-danger/80 hover:bg-dk-3',
    ghost: 'text-dk-5 hover:bg-dk-3'
  }
  
  const sizeClasses = {
    sm: 'px-3 py-1 text-sm',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base'
  }
  
  const className = `${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]}`
  
  return (
    <button 
      type="button" 
      disabled={disabled} 
      className={className}
      {...rest}
    >
      {children}
    </button>
  )
}
