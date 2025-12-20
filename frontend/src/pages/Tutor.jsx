import { useEffect, useState } from 'react'
import LessonList from '../components/LessonList'
import LexChat from '../components/LexChat'
import PodcastPlayer from '../components/PodcastPlayer'

// API base URL
const API_URL = import.meta.env.VITE_API_URL || ''

/**
 * Tutor Page
 *
 * Main learning interface with:
 * - Lex chat for URL input and interaction
 * - Lesson list showing available lessons
 * - Podcast player with transcript
 */
function Tutor({ session, setSession }) {
  const [lessons, setLessons] = useState([])
  const [selectedLesson, setSelectedLesson] = useState(null)
  const [currentLesson, setCurrentLesson] = useState(null)
  const [loadingLesson, setLoadingLesson] = useState(null)
  const [error, setError] = useState(null)
  const [isPolling, setIsPolling] = useState(false)

  // Fetch session data when session changes, with polling for processing sessions
  useEffect(() => {
    if (session?.sessionId) {
      fetchSession(session.sessionId)
    }
  }, [session?.sessionId])

  // Polling effect - fetch until lessons are ready
  useEffect(() => {
    let pollInterval
    if (isPolling && session?.sessionId) {
      pollInterval = setInterval(() => {
        fetchSession(session.sessionId)
      }, 3000) // Poll every 3 seconds
    }
    return () => {
      if (pollInterval) clearInterval(pollInterval)
    }
  }, [isPolling, session?.sessionId])

  // Fetch session details from API
  const fetchSession = async (sessionId) => {
    try {
      const response = await fetch(`${API_URL}/api/session/${sessionId}`)
      if (!response.ok) throw new Error('Failed to fetch session')

      const data = await response.json()
      setLessons(data.lessons || [])
      setError(null)

      // Stop polling if lessons are ready or status is 'ready'/'error'
      if (data.lessons?.length > 0 || data.status === 'ready' || data.status === 'error') {
        setIsPolling(false)
      } else if (data.status === 'processing' || data.status === 'extracting' || data.status === 'planning') {
        // Keep polling if still processing
        setIsPolling(true)
      }
    } catch (err) {
      console.error('Error fetching session:', err)
      // Don't set error - session might not exist yet
    }
  }

  // Handle session creation from Lex
  const handleSessionCreated = (newSession) => {
    setSession(newSession)
    // Start polling for lessons - they may still be processing
    setIsPolling(true)
    // Set initial lessons if provided
    setLessons(newSession.lessons?.map((title, i) => ({
      title,
      lesson_number: i + 1,
      has_audio: false
    })) || [])
  }

  // Handle lesson selection
  const handleSelectLesson = async (lessonNum) => {
    setSelectedLesson(lessonNum)

    // Check if we have a session
    if (!session?.sessionId) {
      // Demo mode - show mock content
      setCurrentLesson({
        title: `Demo Lesson ${lessonNum}`,
        lesson_number: lessonNum,
        audioUrl: null,
        transcript: [
          { speaker: 'alex', text: "Welcome to this demo lesson! In production, you'd hear me explaining the content from your URL.", segment_type: 'intro' },
          { speaker: 'sam', text: "That sounds great, Alex! What will we cover today?", segment_type: 'intro' },
          { speaker: 'alex', text: "We'll break down the key concepts and make them easy to understand with real-world examples.", segment_type: 'discussion' },
          { speaker: 'sam', text: "I love how you always make complex topics accessible. Let's dive in!", segment_type: 'discussion' },
        ]
      })
      return
    }

    // Fetch lesson details
    try {
      setLoadingLesson(lessonNum)

      const response = await fetch(`${API_URL}/api/lesson/${session.sessionId}/${lessonNum}`)
      if (!response.ok) throw new Error('Failed to fetch lesson')

      const data = await response.json()

      // If no audio, generate it
      if (!data.audio_url) {
        await generateLessonAudio(lessonNum)
      } else {
        setCurrentLesson({
          title: data.title,
          lesson_number: lessonNum,
          audioUrl: data.audio_url,
          transcript: data.script
        })
      }

    } catch (err) {
      console.error('Error loading lesson:', err)
      setError('Failed to load lesson. Please try again.')
    } finally {
      setLoadingLesson(null)
    }
  }

  // Generate audio for a lesson
  const generateLessonAudio = async (lessonNum) => {
    try {
      setLoadingLesson(lessonNum)

      const response = await fetch(
        `${API_URL}/api/lesson/${session.sessionId}/${lessonNum}/generate`,
        { method: 'POST' }
      )

      if (!response.ok) throw new Error('Failed to generate audio')

      const data = await response.json()

      setCurrentLesson({
        title: data.title || `Lesson ${lessonNum}`,
        lesson_number: lessonNum,
        audioUrl: data.audio_url,
        transcript: data.transcript
      })

      // Update lessons list
      setLessons(prev => prev.map((l, i) =>
        i === lessonNum - 1 ? { ...l, has_audio: true } : l
      ))

    } catch (err) {
      console.error('Error generating audio:', err)
      setError('Failed to generate audio. Please try again.')
    } finally {
      setLoadingLesson(null)
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="grid lg:grid-cols-2 gap-8">
        {/* Left column - Chat */}
        <div className="space-y-6">
          <div className="card p-6" style={{ height: '500px' }}>
            <h2 className="text-lg font-semibold text-white mb-4">
              💬 Chat with AI Tutor
            </h2>
            <div className="h-[calc(100%-2rem)]">
              <LexChat
                onSessionCreated={handleSessionCreated}
              />
            </div>
          </div>

          {/* Lessons list */}
          <div className="card p-6">
            <LessonList
              lessons={lessons}
              onSelectLesson={handleSelectLesson}
              selectedLesson={selectedLesson}
              loadingLesson={loadingLesson}
            />
          </div>
        </div>

        {/* Right column - Player */}
        <div>
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-4 text-red-400">
              {error}
              <button
                onClick={() => setError(null)}
                className="ml-2 underline"
              >
                Dismiss
              </button>
            </div>
          )}

          {currentLesson ? (
            <PodcastPlayer
              audioUrl={currentLesson.audioUrl}
              transcript={currentLesson.transcript}
              title={currentLesson.title}
              lessonNumber={currentLesson.lesson_number}
            />
          ) : (
            <div className="card p-12 text-center">
              <div className="text-6xl mb-6">🎧</div>
              <h3 className="text-xl font-semibold text-white mb-2">
                Ready to Learn?
              </h3>
              <p className="text-gray-400 max-w-sm mx-auto">
                Share a URL in the chat to create lessons, or select a lesson from the list to start listening.
              </p>

              <div className="mt-8 p-4 bg-slate-800/50 rounded-lg text-left">
                <p className="text-sm text-gray-500 mb-2">Try these:</p>
                <ul className="text-sm text-gray-400 space-y-1">
                  <li>• Documentation pages</li>
                  <li>• Technical blog posts</li>
                  <li>• Tutorial articles</li>
                  <li>• Wikipedia entries</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Tutor
