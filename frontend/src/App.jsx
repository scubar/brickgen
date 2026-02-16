import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Header from './components/Header'
import ApiErrorProvider from './components/ApiErrorProvider'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import LoginPage from './pages/LoginPage'
import SearchPage from './pages/SearchPage'
import SetDetailPage from './pages/SetDetailPage'
import SettingsPage from './pages/SettingsPage'
import ProjectsPage from './pages/ProjectsPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import AttributionsPage from './pages/AttributionsPage'
import DocumentationPage from './pages/DocumentationPage'

function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-dk-6">Loading...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return children
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <div className="min-h-screen bg-dk-1 flex flex-col pb-16">
          <Header />
          <main className="container mx-auto px-4 py-8 flex-1">
            <ApiErrorProvider>
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/" element={<ProtectedRoute><SearchPage /></ProtectedRoute>} />
                <Route path="/set/:setNum" element={<ProtectedRoute><SetDetailPage /></ProtectedRoute>} />
                <Route path="/projects" element={<ProtectedRoute><ProjectsPage /></ProtectedRoute>} />
                <Route path="/projects/:projectId" element={<ProtectedRoute><ProjectDetailPage /></ProtectedRoute>} />
                <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
                <Route path="/settings/cache" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
                <Route path="/settings/database" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
                <Route path="/guide" element={<ProtectedRoute><DocumentationPage /></ProtectedRoute>} />
                <Route path="/attributions" element={<ProtectedRoute><AttributionsPage /></ProtectedRoute>} />
              </Routes>
            </ApiErrorProvider>
          </main>
          <footer className="border-t border-dk-3 bg-dk-2 mt-auto py-3 px-4 text-center text-sm text-dk-5">
            This project is not compatible with LEGO&trade;. LEGO&trade; is a trademark of the LEGO Group, which does not sponsor, authorize or endorse this project.
          </footer>
        </div>
      </AuthProvider>
    </Router>
  )
}

export default App
