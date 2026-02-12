/**
 * Central API client. Use apiFetch() instead of fetch() so non-2xx responses
 * are automatically shown in the global API error banner (when ApiErrorProvider is mounted).
 */

/**
 * Parse a non-2xx fetch Response into an error object for display.
 * Handles FastAPI-style { detail: string | Array<{ loc, msg, ... }> }.
 * @param {Response} response - fetch Response (assumed !response.ok)
 * @returns {Promise<{ status: number, statusText: string, detail: string }>}
 */
export async function parseApiError(response) {
  const status = response.status
  const statusText = response.statusText || 'Error'
  let detail = statusText
  try {
    const body = await response.json()
    const d = body.detail
    if (typeof d === 'string') {
      detail = d
    } else if (Array.isArray(d)) {
      detail = d.map((e) => e.msg || JSON.stringify(e)).join(' ')
    } else if (d != null) {
      detail = String(d)
    }
  } catch {
    try {
      const text = await response.text()
      if (text) detail = text
    } catch {
      // keep default detail
    }
  }
  return { status, statusText, detail }
}

/** Set by ApiErrorProvider on mount. Called when apiFetch gets a non-2xx response. */
let setApiErrorRef = null

/**
 * Register the function that will be called to show API errors (called by ApiErrorProvider).
 * @param {(error: { status, statusText, detail } | null) => void} setter
 */
export function injectApiErrorSetter(setter) {
  setApiErrorRef = setter
}

/**
 * Same as fetch(), but on non-2xx response parses the error and notifies the global
 * error display (if ApiErrorProvider is mounted). Always returns the Response so
 * callers can still check response.ok and handle body as needed.
 * Automatically adds JWT token from localStorage if available.
 * @param {Parameters<typeof fetch>} args - Same as fetch(url, options)
 * @returns {Promise<Response>}
 */
export async function apiFetch(...args) {
  // Add Authorization header if token exists
  const token = localStorage.getItem('auth_token')
  if (token) {
    const [url, options = {}] = args
    const headers = new Headers(options.headers || {})
    headers.set('Authorization', `Bearer ${token}`)
    args = [url, { ...options, headers }]
  }

  const response = await fetch(...args)

  // If unauthorized, dispatch custom event to trigger logout
  if (response.status === 401) {
    localStorage.removeItem('auth_token')
    // Dispatch custom event that AuthContext can listen for
    window.dispatchEvent(new CustomEvent('auth:unauthorized'))
  }

  if (!response.ok && setApiErrorRef) {
    try {
      const error = await parseApiError(response.clone())
      setApiErrorRef(error)
    } catch (e) {
      setApiErrorRef({
        status: response.status,
        statusText: response.statusText || 'Error',
        detail: response.statusText || 'Request failed'
      })
    }
  }
  return response
}
