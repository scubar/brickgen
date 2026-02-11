import { useState, useEffect } from 'react'

/**
 * Display an API error (e.g. from api.parseApiError or the global apiFetch interceptor).
 * @param {Object} props
 * @param {{ status?: number, statusText?: string, detail: string }|null} props.error - Error object from parseApiError, or null to render nothing
 * @param {() => void} [props.onDismiss] - Called when user dismisses the alert
 * @param {string} [props.className] - Extra class names for the container
 */
export default function ApiErrorDisplay({ error, onDismiss, className = '' }) {
  const [dismissed, setDismissed] = useState(false)
  useEffect(() => {
    if (error?.detail) setDismissed(false)
  }, [error?.detail])

  if (!error?.detail || dismissed) return null

  const handleDismiss = () => {
    setDismissed(true)
    onDismiss?.()
  }

  return (
    <div
      role="alert"
      className={`rounded-lg border border-danger/40 bg-danger/10 text-danger px-4 py-3 ${className}`}
    >
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          {error.status != null && (
            <span className="font-semibold text-danger/90">
              {error.status} {error.statusText || 'Error'}
            </span>
          )}
          {error.status != null && <span className="mx-2">·</span>}
          <span className="break-words">{error.detail}</span>
        </div>
        <button
          type="button"
          onClick={handleDismiss}
          className="shrink-0 p-1 rounded hover:bg-danger/20 text-danger focus:outline-none focus:ring-2 focus:ring-danger/50"
          aria-label="Dismiss"
        >
          ✕
        </button>
      </div>
    </div>
  )
}
