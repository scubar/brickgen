import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Header from './components/Header'
import ApiErrorProvider from './components/ApiErrorProvider'
import SearchPage from './pages/SearchPage'
import SetDetailPage from './pages/SetDetailPage'
import SettingsPage from './pages/SettingsPage'
import ProjectsPage from './pages/ProjectsPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import AttributionsPage from './pages/AttributionsPage'
import DocumentationPage from './pages/DocumentationPage'
function App() {
  return (
    <Router>
      <div className="min-h-screen bg-dk-1 flex flex-col pb-16">
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
        <footer className="border-t border-dk-3 bg-dk-2 py-3 px-4 text-center text-sm text-dk-5 fixed bottom-0 left-0 right-0">
          This project is not compatible with LEGO&trade;. LEGO&trade; is a trademark of the LEGO Group, which does not sponsor, authorize or endorse this project.
        </footer>
      </div>
    </Router>
  )
}

export default App
