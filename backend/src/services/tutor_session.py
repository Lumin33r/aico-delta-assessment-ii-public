"""
Tutor Session Manager

Manages the complete tutoring session lifecycle, integrating all services:
- Content extraction and processing
- Podcast script generation
- Audio synthesis
- Progress tracking

This is the main orchestration layer for the AI Personal Tutor.
"""

import os
import uuid
import logging
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

from .content_extractor import ContentExtractor
from .content_processor import ContentProcessor, ProcessedContent
from .podcast_generator import PodcastGenerator
from .dialogue_models import (
    EpisodeScript, EpisodeSegment, DialogueTurn,
    Speaker, SegmentType, validate_script
)
from .script_formatter import ScriptFormatter
from .enhanced_audio_synthesizer import (
    EnhancedAudioSynthesizer, SynthesisConfig, SynthesisResult
)
from .audio_coordinator import AudioCoordinator, SynthesisJob, JobStatus

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Status of a tutoring session."""
    CREATED = "created"
    VALIDATING = "validating"
    EXTRACTING = "extracting"
    PROCESSING = "processing"
    PLANNING = "planning"
    READY = "ready"
    GENERATING = "generating"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class LessonInfo:
    """Information about a single lesson in a session."""
    lesson_number: int
    title: str
    description: str = ""
    key_concepts: List[str] = field(default_factory=list)

    # Generation state
    script: Optional[EpisodeScript] = None
    audio_result: Optional[SynthesisResult] = None

    # Timing
    estimated_duration_minutes: float = 10.0
    actual_duration_seconds: float = 0.0

    # Status
    script_generated: bool = False
    audio_generated: bool = False
    generation_error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'lesson_number': self.lesson_number,
            'title': self.title,
            'description': self.description,
            'key_concepts': self.key_concepts,
            'estimated_duration_minutes': self.estimated_duration_minutes,
            'actual_duration_seconds': self.actual_duration_seconds,
            'script_generated': self.script_generated,
            'audio_generated': self.audio_generated,
            'audio_url': self.audio_result.audio_url if self.audio_result else None,
            'generation_error': self.generation_error
        }


@dataclass
class TutorSessionData:
    """
    Complete tutoring session data.

    Tracks the full lifecycle from URL ingestion to audio generation.
    """
    session_id: str
    source_url: str
    status: SessionStatus = SessionStatus.CREATED

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    # Content
    raw_content: Optional[Dict] = None
    processed_content: Optional[ProcessedContent] = None

    # Lessons
    lessons: List[LessonInfo] = field(default_factory=list)
    total_lessons: int = 0

    # Progress
    current_step: str = ""
    progress_percent: float = 0.0

    # Errors
    error_message: Optional[str] = None

    # Metadata
    user_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Serialize session to dictionary."""
        return {
            'session_id': self.session_id,
            'source_url': self.source_url,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'content_summary': {
                'title': self.processed_content.title if self.processed_content else None,
                'word_count': self.processed_content.total_words if self.processed_content else 0,
                'reading_time_minutes': self.processed_content.reading_time_minutes if self.processed_content else 0,
                'topics': self.processed_content.topics if self.processed_content else [],
                'key_concepts': self.processed_content.key_concepts[:10] if self.processed_content else []
            } if self.processed_content else None,
            'lessons': [lesson.to_dict() for lesson in self.lessons],
            'total_lessons': self.total_lessons,
            'current_step': self.current_step,
            'progress_percent': self.progress_percent,
            'error_message': self.error_message,
            'user_id': self.user_id,
            'metadata': self.metadata
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class TutorSessionManager:
    """
    Manages tutoring sessions end-to-end.

    Coordinates:
    - Content extraction and processing
    - Lesson plan generation
    - Script generation for each lesson
    - Audio synthesis
    - Progress tracking
    """

    def __init__(
        self,
        extractor: Optional[ContentExtractor] = None,
        processor: Optional[ContentProcessor] = None,
        generator: Optional[PodcastGenerator] = None,
        formatter: Optional[ScriptFormatter] = None,
        synthesizer: Optional[EnhancedAudioSynthesizer] = None,
        coordinator: Optional[AudioCoordinator] = None
    ):
        """
        Initialize the session manager.

        Args:
            extractor: Content extractor instance
            processor: Content processor instance
            generator: Podcast generator instance
            formatter: Script formatter instance
            synthesizer: Audio synthesizer instance
            coordinator: Audio coordinator instance
        """
        self.extractor = extractor or ContentExtractor()
        self.processor = processor or ContentProcessor()
        self.generator = generator or PodcastGenerator()
        self.formatter = formatter or ScriptFormatter()
        self.synthesizer = synthesizer or EnhancedAudioSynthesizer()
        self.coordinator = coordinator or AudioCoordinator(
            synthesizer=self.synthesizer,
            generator=self.generator,
            formatter=self.formatter
        )

        # Session storage (in-memory, can be replaced with Redis/DB)
        self._sessions: Dict[str, TutorSessionData] = {}

        # Progress callbacks
        self._progress_callbacks: List[Callable[[TutorSessionData], None]] = []

    def add_progress_callback(
        self,
        callback: Callable[[TutorSessionData], None]
    ) -> None:
        """Add callback for session progress updates."""
        self._progress_callbacks.append(callback)

    def _notify_progress(self, session: TutorSessionData) -> None:
        """Notify all progress callbacks."""
        session.updated_at = datetime.now(timezone.utc)
        for callback in self._progress_callbacks:
            try:
                callback(session)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

    def create_session(
        self,
        url: str,
        num_lessons: int = 3,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> TutorSessionData:
        """
        Create a new tutoring session.

        This is the main entry point for the tutoring workflow.
        It extracts content, creates a lesson plan, but does NOT
        generate scripts or audio (those are on-demand).

        Args:
            url: URL to extract content from
            num_lessons: Number of lessons to plan
            user_id: Optional user identifier
            metadata: Optional session metadata

        Returns:
            TutorSessionData with session information
        """
        # Create session
        session_id = str(uuid.uuid4())
        session = TutorSessionData(
            session_id=session_id,
            source_url=url,
            user_id=user_id,
            metadata=metadata or {}
        )
        self._sessions[session_id] = session

        logger.info(f"Created session {session_id} for URL: {url}")

        try:
            # Step 1: Extract content
            session.status = SessionStatus.EXTRACTING
            session.current_step = "Extracting content from URL"
            session.progress_percent = 10
            self._notify_progress(session)

            raw_content = self.extractor.extract(url)
            session.raw_content = raw_content

            logger.info(f"Extracted {len(raw_content.get('text', ''))} chars")

            # Step 2: Process content
            session.status = SessionStatus.PROCESSING
            session.current_step = "Processing and analyzing content"
            session.progress_percent = 30
            self._notify_progress(session)

            processed = self.processor.process(raw_content)
            session.processed_content = processed

            logger.info(f"Processed: {len(processed.chunks)} chunks, {len(processed.topics)} topics")

            # Step 3: Generate lesson plan
            session.status = SessionStatus.PLANNING
            session.current_step = "Creating lesson plan"
            session.progress_percent = 50
            self._notify_progress(session)

            # Check if generator is available
            if not self.generator.check_health():
                raise RuntimeError("Ollama is not available for lesson planning")

            topics = self.generator.create_lesson_plan(
                content=raw_content['text'],
                title=raw_content.get('title', 'Untitled'),
                num_lessons=num_lessons
            )

            # Create lesson info objects
            session.lessons = [
                LessonInfo(
                    lesson_number=i + 1,
                    title=topic.get('title', f'Lesson {i + 1}'),
                    description=topic.get('description', ''),
                    key_concepts=topic.get('key_concepts', []),
                    estimated_duration_minutes=10.0
                )
                for i, topic in enumerate(topics)
            ]
            session.total_lessons = len(session.lessons)

            logger.info(f"Created {len(topics)} lessons")

            # Ready for lesson generation
            session.status = SessionStatus.READY
            session.current_step = "Ready - request lesson generation"
            session.progress_percent = 100
            self._notify_progress(session)

        except Exception as e:
            logger.error(f"Session creation failed: {e}")
            session.status = SessionStatus.ERROR
            session.error_message = str(e)
            session.current_step = "Error occurred"
            self._notify_progress(session)

        return session

    def generate_lesson(
        self,
        session_id: str,
        lesson_number: int,
        generate_audio: bool = True,
        target_duration_minutes: int = 10
    ) -> LessonInfo:
        """
        Generate script and optionally audio for a specific lesson.

        Args:
            session_id: Session identifier
            lesson_number: Lesson number (1-indexed)
            generate_audio: Whether to also generate audio
            target_duration_minutes: Target duration for the episode

        Returns:
            Updated LessonInfo with generated content
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if session.status not in [SessionStatus.READY, SessionStatus.GENERATING, SessionStatus.COMPLETE]:
            raise ValueError(f"Session not ready: {session.status.value}")

        if lesson_number < 1 or lesson_number > len(session.lessons):
            raise ValueError(f"Invalid lesson number: {lesson_number}")

        lesson = session.lessons[lesson_number - 1]

        # Check if already generated
        if lesson.audio_generated and generate_audio:
            logger.info(f"Lesson {lesson_number} already generated")
            return lesson

        session.status = SessionStatus.GENERATING
        session.current_step = f"Generating lesson {lesson_number}"
        self._notify_progress(session)

        try:
            # Generate script
            if not lesson.script_generated:
                logger.info(f"Generating script for lesson {lesson_number}")

                topic = {
                    'title': lesson.title,
                    'description': lesson.description,
                    'key_concepts': lesson.key_concepts
                }

                script = self.generator.generate_episode(
                    topic=topic,
                    content=session.raw_content['text'],
                    lesson_number=lesson_number,
                    total_lessons=session.total_lessons,
                    target_duration=target_duration_minutes
                )

                lesson.script = script
                lesson.script_generated = True
                lesson.estimated_duration_minutes = script.estimated_duration_minutes

                logger.info(f"Script generated: {script.total_words} words")

            # Generate audio
            if generate_audio and not lesson.audio_generated:
                logger.info(f"Generating audio for lesson {lesson_number}")

                job = self.coordinator.process_episode(
                    script=lesson.script,
                    session_id=session_id,
                    upload_to_s3=True
                )

                if job.status == JobStatus.COMPLETED and job.result:
                    lesson.audio_result = job.result
                    lesson.audio_generated = True
                    lesson.actual_duration_seconds = job.result.duration_seconds

                    logger.info(f"Audio generated: {job.result.duration_seconds:.1f}s")
                else:
                    lesson.generation_error = job.error or "Audio generation failed"

            # Update session status
            all_generated = all(l.audio_generated for l in session.lessons)
            session.status = SessionStatus.COMPLETE if all_generated else SessionStatus.READY
            session.current_step = "Complete" if all_generated else "Ready"
            self._notify_progress(session)

        except Exception as e:
            logger.error(f"Lesson generation failed: {e}")
            lesson.generation_error = str(e)
            session.status = SessionStatus.READY  # Allow retry
            session.current_step = f"Error generating lesson {lesson_number}"
            self._notify_progress(session)

        return lesson

    def generate_all_lessons(
        self,
        session_id: str,
        generate_audio: bool = True
    ) -> TutorSessionData:
        """
        Generate all lessons for a session.

        Args:
            session_id: Session identifier
            generate_audio: Whether to generate audio for all

        Returns:
            Updated session data
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        for i in range(len(session.lessons)):
            self.generate_lesson(
                session_id=session_id,
                lesson_number=i + 1,
                generate_audio=generate_audio
            )

        return session

    def get_session(self, session_id: str) -> Optional[TutorSessionData]:
        """Get session by ID."""
        return self._sessions.get(session_id)

    def get_lesson(
        self,
        session_id: str,
        lesson_number: int
    ) -> Optional[LessonInfo]:
        """Get specific lesson from a session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        if lesson_number < 1 or lesson_number > len(session.lessons):
            return None

        return session.lessons[lesson_number - 1]

    def get_transcript(
        self,
        session_id: str,
        lesson_number: int,
        format: str = "markdown"
    ) -> Optional[str]:
        """
        Get transcript for a lesson.

        Args:
            session_id: Session identifier
            lesson_number: Lesson number
            format: Output format (markdown, plain, srt)

        Returns:
            Formatted transcript string
        """
        lesson = self.get_lesson(session_id, lesson_number)
        if not lesson or not lesson.script:
            return None

        return self.formatter.generate_transcript(lesson.script, format)

    def get_audio_url(
        self,
        session_id: str,
        lesson_number: int,
        fresh: bool = True
    ) -> Optional[str]:
        """
        Get audio URL for a lesson.

        Args:
            session_id: Session identifier
            lesson_number: Lesson number
            fresh: Generate fresh presigned URL

        Returns:
            Audio URL or None
        """
        lesson = self.get_lesson(session_id, lesson_number)
        if not lesson or not lesson.audio_result:
            return None

        if fresh and lesson.audio_result.s3_key:
            return self.synthesizer.get_presigned_url(lesson.audio_result.s3_key)

        return lesson.audio_result.audio_url

    def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[SessionStatus] = None
    ) -> List[TutorSessionData]:
        """
        List sessions with optional filtering.

        Args:
            user_id: Filter by user ID
            status: Filter by status

        Returns:
            List of matching sessions
        """
        sessions = list(self._sessions.values())

        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]

        if status:
            sessions = [s for s in sessions if s.status == status]

        return sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """
        Remove sessions older than max_age_hours.

        Args:
            max_age_hours: Maximum session age

        Returns:
            Number of sessions removed
        """
        now = datetime.now(timezone.utc)
        to_remove = []

        for session_id, session in self._sessions.items():
            age_hours = (now - session.created_at).total_seconds() / 3600
            if age_hours > max_age_hours:
                to_remove.append(session_id)

        for session_id in to_remove:
            del self._sessions[session_id]

        return len(to_remove)

    def check_health(self) -> Dict[str, Any]:
        """
        Check health of all components.

        Returns:
            Health status dict
        """
        return {
            'session_manager': True,
            'active_sessions': len(self._sessions),
            'extractor': True,  # ContentExtractor is always available
            'processor': True,  # ContentProcessor is always available
            'generator': self.generator.check_health(),
            'synthesizer': self.synthesizer.check_health(),
            'coordinator': self.coordinator.check_health()
        }


# =============================================================================
# Convenience Functions
# =============================================================================

# Global instance for simple usage
_default_manager: Optional[TutorSessionManager] = None


def get_manager() -> TutorSessionManager:
    """Get or create the default session manager."""
    global _default_manager
    if _default_manager is None:
        _default_manager = TutorSessionManager()
    return _default_manager


def create_lesson_from_url(
    url: str,
    num_lessons: int = 3,
    generate_audio: bool = False
) -> TutorSessionData:
    """
    Quick function to create lessons from a URL.

    Args:
        url: URL to extract content from
        num_lessons: Number of lessons to create
        generate_audio: Whether to generate audio immediately

    Returns:
        Session data with lessons
    """
    manager = get_manager()
    session = manager.create_session(url, num_lessons)

    if generate_audio and session.status == SessionStatus.READY:
        session = manager.generate_all_lessons(session.session_id, generate_audio=True)

    return session


# =============================================================================
# Demo
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Tutor Session Manager")
    print("=" * 40)

    manager = TutorSessionManager()
    health = manager.check_health()

    print("\nComponent Health:")
    for component, status in health.items():
        if isinstance(status, dict):
            print(f"  {component}:")
            for k, v in list(status.items())[:5]:
                icon = "✓" if v else "✗"
                print(f"    {icon} {k}: {v}")
        else:
            icon = "✓" if status else "✗"
            print(f"  {icon} {component}: {status}")

    print("\nUsage:")
    print("""
    manager = TutorSessionManager()

    # Create session from URL
    session = manager.create_session(
        url="https://example.com/article",
        num_lessons=3
    )

    # Generate a specific lesson
    lesson = manager.generate_lesson(
        session_id=session.session_id,
        lesson_number=1,
        generate_audio=True
    )

    # Get transcript
    transcript = manager.get_transcript(
        session_id=session.session_id,
        lesson_number=1,
        format="markdown"
    )

    # Get audio URL
    audio_url = manager.get_audio_url(
        session_id=session.session_id,
        lesson_number=1
    )
    """)
