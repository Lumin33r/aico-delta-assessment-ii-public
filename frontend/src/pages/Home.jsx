import { Link } from 'react-router-dom'

/**
 * Home Page
 *
 * Landing page with app introduction and features.
 */
function Home() {
  return (
    <div className="min-h-[calc(100vh-200px)] flex flex-col items-center justify-center px-4 py-12">
      {/* Hero section */}
      <div className="text-center max-w-3xl mx-auto mb-12">
        <h1 className="text-5xl font-bold mb-6">
          <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
            Learn Anything
          </span>
          <br />
          <span className="text-white">from Any URL</span>
        </h1>

        <p className="text-xl text-gray-400 mb-8">
          Transform web content into engaging podcast-style lessons with AI hosts
          who make learning feel like listening to your favorite show.
        </p>

        <Link to="/tutor" className="btn btn-primary text-lg px-8 py-3">
          Start Learning →
        </Link>
      </div>

      {/* Hosts section */}
      <div className="grid md:grid-cols-2 gap-6 max-w-2xl mx-auto mb-12">
        <div className="card p-6 text-center">
          <div className="w-16 h-16 rounded-full bg-blue-500/20 flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl">👨‍💻</span>
          </div>
          <h3 className="text-lg font-semibold text-blue-400 mb-2">Alex</h3>
          <p className="text-sm text-gray-400">
            Senior Engineer • Matthew Voice
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Patient expert who explains complex concepts with great analogies
          </p>
        </div>

        <div className="card p-6 text-center">
          <div className="w-16 h-16 rounded-full bg-purple-500/20 flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl">👩‍💻</span>
          </div>
          <h3 className="text-lg font-semibold text-purple-400 mb-2">Sam</h3>
          <p className="text-sm text-gray-400">
            Curious Learner • Joanna Voice
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Asks the questions you're thinking and summarizes key points
          </p>
        </div>
      </div>

      {/* Features */}
      <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
        <div className="card p-6">
          <div className="text-3xl mb-4">🔗</div>
          <h3 className="font-semibold text-white mb-2">Share Any URL</h3>
          <p className="text-sm text-gray-400">
            Paste documentation, articles, tutorials - any web content you want to learn from.
          </p>
        </div>

        <div className="card p-6">
          <div className="text-3xl mb-4">🎙️</div>
          <h3 className="font-semibold text-white mb-2">Podcast Lessons</h3>
          <p className="text-sm text-gray-400">
            Two AI hosts discuss the topic in an engaging, educational conversation.
          </p>
        </div>

        <div className="card p-6">
          <div className="text-3xl mb-4">🧠</div>
          <h3 className="font-semibold text-white mb-2">Deep Understanding</h3>
          <p className="text-sm text-gray-400">
            Concepts explained with analogies, examples, and natural dialogue.
          </p>
        </div>
      </div>

      {/* Tech stack */}
      <div className="mt-16 text-center">
        <p className="text-sm text-gray-600 mb-4">Powered by</p>
        <div className="flex items-center justify-center gap-6 text-gray-500 text-sm">
          <span>AWS Polly</span>
          <span>•</span>
          <span>Amazon Lex</span>
          <span>•</span>
          <span>Ollama</span>
          <span>•</span>
          <span>React + Vite</span>
        </div>
      </div>
    </div>
  )
}

export default Home
