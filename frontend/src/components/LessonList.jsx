
/**
 * LessonList Component
 *
 * Displays available lessons for a session with status indicators.
 */
function LessonList({ lessons, onSelectLesson, selectedLesson, loadingLesson }) {
  if (!lessons || lessons.length === 0) {
    return (
      <div className="card p-6 text-center">
        <p className="text-gray-400">No lessons available yet.</p>
        <p className="text-sm text-gray-500 mt-2">
          Share a URL in the chat to create lessons!
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-white mb-4">Your Lessons</h3>

      {lessons.map((lesson, index) => {
        const lessonNum = index + 1
        const isSelected = selectedLesson === lessonNum
        const isLoading = loadingLesson === lessonNum

        return (
          <button
            key={lessonNum}
            onClick={() => onSelectLesson(lessonNum)}
            disabled={isLoading}
            className={`lesson-card w-full text-left ${
              isSelected ? 'border-indigo-500 bg-indigo-500/10' : ''
            } ${isLoading ? 'opacity-50 cursor-wait' : ''}`}
          >
            {/* Lesson number */}
            <div className={`lesson-number ${isSelected ? 'bg-indigo-500' : ''}`}>
              {isLoading ? (
                <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                lessonNum
              )}
            </div>

            {/* Lesson info */}
            <div className="flex-1 min-w-0">
              <h4 className="font-medium text-white truncate">
                {lesson.title || `Lesson ${lessonNum}`}
              </h4>
              {lesson.topic && (
                <p className="text-sm text-gray-400 truncate">
                  {lesson.topic.description || lesson.topic}
                </p>
              )}
            </div>

            {/* Status indicator */}
            <div className="flex items-center gap-2">
              {lesson.has_audio ? (
                <span className="flex items-center gap-1 text-sm text-emerald-400">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  Ready
                </span>
              ) : (
                <span className="text-sm text-gray-500">
                  Generate →
                </span>
              )}
            </div>
          </button>
        )
      })}
    </div>
  )
}

export default LessonList
