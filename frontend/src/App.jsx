import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Header from './components/Header'
import SearchPage from './pages/SearchPage'
import SetDetailPage from './pages/SetDetailPage'
import SettingsPage from './pages/SettingsPage'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-100">
        <Header />
        <main className="container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<SearchPage />} />
            <Route path="/set/:setNum" element={<SetDetailPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
