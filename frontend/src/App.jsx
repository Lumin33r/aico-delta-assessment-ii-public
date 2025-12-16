import { useState } from 'react'
import { Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import './index.css'
import Home from './pages/Home'
import Tutor from './pages/Tutor'

/**
 * AI Personal Tutor Application
 *
 * Main application component with routing.
 * Features:
 * - Amazon Lex chat interface for conversational onboarding
 * - Podcast-style lessons with two AI hosts (Alex & Sam)
 * - URL content extraction and lesson generation
 */
function App() {
  const [session, setSession] = useState(null)

  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route
            path="/tutor"
            element={<Tutor session={session} setSession={setSession} />}
          />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
