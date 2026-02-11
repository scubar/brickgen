import { useState, useEffect, useRef } from 'react'
import { injectApiErrorSetter } from '../api'
import ApiErrorDisplay from './ApiErrorDisplay'

const AUTO_CLEAR_MS = 15_000

/**
 * Provider that mounts the global API error interceptor and renders the error banner.
 * Errors auto-clear after 15 seconds; a new error replaces the current one and restarts the timer.
 */
export default function ApiErrorProvider({ children }) {
  const [apiError, setApiError] = useState(null)
  const clearTimerRef = useRef(null)

  useEffect(() => {
    const setError = (error) => {
      if (clearTimerRef.current) {
        clearTimeout(clearTimerRef.current)
        clearTimerRef.current = null
      }
      setApiError(error)
      if (error) {
        clearTimerRef.current = setTimeout(() => {
          setApiError(null)
          clearTimerRef.current = null
        }, AUTO_CLEAR_MS)
      }
    }
    injectApiErrorSetter(setError)
    return () => {
      injectApiErrorSetter(null)
      if (clearTimerRef.current) {
        clearTimeout(clearTimerRef.current)
      }
    }
  }, [])

  return (
    <>
      <ApiErrorDisplay
        error={apiError}
        onDismiss={() => setApiError(null)}
        className="mb-4"
      />
      {children}
    </>
  )
}
