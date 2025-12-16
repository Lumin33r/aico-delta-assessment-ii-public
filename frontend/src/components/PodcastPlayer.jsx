import { useEffect, useRef, useState } from 'react'

/**
 * PodcastPlayer Component
 *
 * Audio player for podcast-style lessons with transcript display.
 * Shows dialogue between Alex and Sam with synchronized highlighting.
 */
function PodcastPlayer({ audioUrl, transcript, title, lessonNumber }) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [showTranscript, setShowTranscript] = useState(true)
  const audioRef = useRef(null)

  // Update time display
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handleTimeUpdate = () => setCurrentTime(audio.currentTime)
    const handleDurationChange = () => setDuration(audio.duration)
    const handleEnded = () => setIsPlaying(false)

    audio.addEventListener('timeupdate', handleTimeUpdate)
    audio.addEventListener('durationchange', handleDurationChange)
    audio.addEventListener('ended', handleEnded)

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate)
      audio.removeEventListener('durationchange', handleDurationChange)
      audio.removeEventListener('ended', handleEnded)
    }
  }, [])

  // Format time as MM:SS
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Toggle play/pause
  const togglePlay = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause()
      } else {
        audioRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }

  // Seek in audio
  const handleSeek = (e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const percentage = x / rect.width
    const newTime = percentage * duration

    if (audioRef.current) {
      audioRef.current.currentTime = newTime
      setCurrentTime(newTime)
    }
  }

  // Skip forward/back
  const skip = (seconds) => {
    if (audioRef.current) {
      audioRef.current.currentTime = Math.max(0, Math.min(duration, currentTime + seconds))
    }
  }

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0

  return (
    <div className="space-y-4">
      {/* Audio element (hidden) */}
      <audio ref={audioRef} src={audioUrl} preload="metadata" />

      {/* Player card */}
      <div className="card p-6">
        {/* Title */}
        <div className="mb-4">
          <span className="text-sm text-indigo-400 font-medium">Lesson {lessonNumber}</span>
          <h3 className="text-xl font-semibold text-white">{title}</h3>
        </div>

        {/* Host badges */}
        <div className="flex gap-2 mb-4">
          <span className="host-badge alex">
            <span className="w-2 h-2 bg-blue-400 rounded-full" />
            Alex (Matthew)
          </span>
          <span className="host-badge sam">
            <span className="w-2 h-2 bg-purple-400 rounded-full" />
            Sam (Joanna)
          </span>
        </div>

        {/* Progress bar */}
        <div
          className="audio-player-progress cursor-pointer mb-3"
          onClick={handleSeek}
        >
          <div
            className="audio-player-progress-bar"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Time display */}
        <div className="flex justify-between text-sm text-gray-400 mb-4">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>

        {/* Controls */}
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={() => skip(-10)}
            className="p-2 text-gray-400 hover:text-white transition-colors"
            title="Back 10 seconds"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0019 16V8a1 1 0 00-1.6-.8l-5.333 4zM4.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0011 16V8a1 1 0 00-1.6-.8l-5.334 4z" />
            </svg>
          </button>

          <button
            onClick={togglePlay}
            className="w-16 h-16 rounded-full bg-indigo-600 hover:bg-indigo-500 flex items-center justify-center transition-colors"
          >
            {isPlaying ? (
              <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
              </svg>
            ) : (
              <svg className="w-8 h-8 text-white ml-1" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            )}
          </button>

          <button
            onClick={() => skip(10)}
            className="p-2 text-gray-400 hover:text-white transition-colors"
            title="Forward 10 seconds"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.933 12.8a1 1 0 000-1.6L6.6 7.2A1 1 0 005 8v8a1 1 0 001.6.8l5.333-4zM19.933 12.8a1 1 0 000-1.6l-5.333-4A1 1 0 0013 8v8a1 1 0 001.6.8l5.333-4z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Transcript toggle */}
      <button
        onClick={() => setShowTranscript(!showTranscript)}
        className="w-full btn btn-secondary flex items-center justify-center gap-2"
      >
        <svg className={`w-5 h-5 transition-transform ${showTranscript ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
        {showTranscript ? 'Hide Transcript' : 'Show Transcript'}
      </button>

      {/* Transcript */}
      {showTranscript && transcript && (
        <div className="card p-4 max-h-96 overflow-y-auto">
          <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
            Transcript
          </h4>
          <div className="space-y-0">
            {transcript.map((segment, index) => (
              <div key={index} className="transcript-segment">
                <div className={`transcript-speaker ${segment.speaker}`}>
                  {segment.speaker === 'alex' ? 'Alex:' : 'Sam:'}
                </div>
                <p className="text-gray-300">{segment.text}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default PodcastPlayer
