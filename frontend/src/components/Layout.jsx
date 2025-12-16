import { Link, useLocation } from 'react-router-dom'

/**
 * Layout component with navigation header and main content area.
 */
function Layout({ children }) {
  const location = useLocation()

  const navLinks = [
    { path: '/', label: 'Home' },
    { path: '/tutor', label: 'Start Learning' },
  ]

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-slate-900/80 backdrop-blur-md border-b border-slate-800 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <span className="text-2xl">🎓</span>
            <span className="text-xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              AI Tutor
            </span>
          </Link>

          <nav className="flex items-center gap-6">
            {navLinks.map(link => (
              <Link
                key={link.path}
                to={link.path}
                className={`text-sm font-medium transition-colors ${
                  location.pathname === link.path
                    ? 'text-indigo-400'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-slate-900/50 border-t border-slate-800 py-6">
        <div className="max-w-6xl mx-auto px-4 text-center text-sm text-gray-500">
          <p>AI Personal Tutor • Powered by AWS Polly, Lex & Ollama</p>
          <p className="mt-2">
            Meet your hosts:
            <span className="text-blue-400 ml-2">Alex (Matthew)</span> &
            <span className="text-purple-400 ml-1">Sam (Joanna)</span>
          </p>
        </div>
      </footer>
    </div>
  )
}

export default Layout
