/**
 * Reusable ProgressBar component for visual progress indication (0-100)
 */
export default function ProgressBar({ value, label, className = '' }) {
  const clampedValue = Math.min(100, Math.max(0, value))
  
  return (
    <div className={className}>
      {label && (
        <div className="text-sm text-dk-5 mb-1">{label}</div>
      )}
      <div className="bg-dk-3 rounded-full h-1.5 overflow-hidden">
        <div 
          className="bg-mint h-1.5 transition-all duration-300"
          style={{ width: `${clampedValue}%` }}
        />
      </div>
    </div>
  )
}
