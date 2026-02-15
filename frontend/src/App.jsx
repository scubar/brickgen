import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Header from './components/Header'
import ApiErrorProvider from './components/ApiErrorProvider'
import OnboardingWizard from './components/OnboardingWizard'
import SearchPage from './pages/SearchPage'
import SetDetailPage from './pages/SetDetailPage'
import SettingsPage from './pages/SettingsPage'
import ProjectsPage from './pages/ProjectsPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import AttributionsPage from './pages/AttributionsPage'
import DocumentationPage from './pages/DocumentationPage'
import { apiFetch } from './api'

function App() {
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [checkingOnboarding, setCheckingOnboarding] = useState(true)

  useEffect(() => {
    checkOnboardingStatus()
  }, [])

  const checkOnboardingStatus = async () => {
    try {
      const r = await apiFetch('/api/settings')
      if (r.ok) {
        const data = await r.json()
        setShowOnboarding(!data.onboarding_wizard_complete)
      }
    } catch (e) {
      console.error('Failed to check onboarding status:', e)
    } finally {
      setCheckingOnboarding(false)
    }
  }

  const handleOnboardingComplete = () => {
    setShowOnboarding(false)
  }

  return (
    <Router>
      <div className="min-h-screen bg-dk-1 flex flex-col">
        <Header />
        <main className="container mx-auto px-4 py-8 flex-1">
          <ApiErrorProvider>
          <Routes>
            <Route path="/" element={<SearchPage />} />
            <Route path="/set/:setNum" element={<SetDetailPage />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/settings/cache" element={<SettingsPage />} />
            <Route path="/settings/database" element={<SettingsPage />} />
            <Route path="/guide" element={<DocumentationPage />} />
            <Route path="/attributions" element={<AttributionsPage />} />
          </Routes>
          </ApiErrorProvider>
        </main>
        <footer className="border-t border-dk-3 bg-dk-2 mt-auto py-3 px-4 text-center text-sm text-dk-5">
          This project is not compatible with LEGO&trade;. LEGO&trade; is a trademark of the LEGO Group, which does not sponsor, authorize or endorse this project.
        </footer>
        
        {/* Show onboarding wizard if not completed */}
        {!checkingOnboarding && showOnboarding && (
          <OnboardingWizard onComplete={handleOnboardingComplete} />
        )}
      </div>
    </Router>
  )
}

export default App
