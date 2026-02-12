import { createContext, useContext, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [user, setUser] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    checkAuth()
    
    // Listen for unauthorized events from apiFetch
    const handleUnauthorized = () => {
      setIsAuthenticated(false)
      setUser(null)
      navigate('/login', { replace: true })
    }
    
    window.addEventListener('auth:unauthorized', handleUnauthorized)
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized)
  }, [navigate])

  const checkAuth = async () => {
    const token = localStorage.getItem('auth_token')
    if (!token) {
      setIsAuthenticated(false)
      setIsLoading(false)
      return
    }

    try {
      const response = await fetch('/api/verify', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setIsAuthenticated(true)
        setUser(data.username)
      } else {
        // Token is invalid
        localStorage.removeItem('auth_token')
        setIsAuthenticated(false)
      }
    } catch (err) {
      console.error('Auth check failed:', err)
      setIsAuthenticated(false)
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem('auth_token')
    setIsAuthenticated(false)
    setUser(null)
    navigate('/login')
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, user, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
