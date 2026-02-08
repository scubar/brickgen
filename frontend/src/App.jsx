import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Header from './components/Header'
import SearchPage from './pages/SearchPage'
import SetDetailPage from './pages/SetDetailPage'
import SettingsPage from './pages/SettingsPage'
import ProjectsPage from './pages/ProjectsPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import AttributionsPage from './pages/AttributionsPage'
function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-100 flex flex-col">
        <Header />
        <main className="container mx-auto px-4 py-8 flex-1">
          <Routes>
            <Route path="/" element={<SearchPage />} />
            <Route path="/set/:setNum" element={<SetDetailPage />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/settings/cache" element={<SettingsPage />} />
            <Route path="/attributions" element={<AttributionsPage />} />
          </Routes>
        </main>
        <footer className="border-t border-gray-200 bg-white mt-auto py-3 px-4 text-center text-sm text-gray-500">
          This project is not compatible with LEGO&trade;. LEGO&trade; is a trademark of the LEGO Group, which does not sponsor, authorize or endorse this project.
        </footer>
      </div>
    </Router>
  )
}

export default App
