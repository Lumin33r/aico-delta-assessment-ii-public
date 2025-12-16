# Backend Services
"""
Service modules for content extraction, podcast generation, and audio synthesis.
"""

from .content_extractor import ContentExtractor
from .content_processor import ContentProcessor, ProcessedContent, ContentChunk
from .podcast_generator import PodcastGenerator
from .audio_synthesizer import AudioSynthesizer
from .dialogue_models import (
    DialogueTurn, EpisodeScript, EpisodeSegment, LessonPlan,
    Speaker, SegmentType, EmotionHint,
    validate_script
)
from .script_formatter import ScriptFormatter, format_for_polly, generate_transcript
from .prompt_templates import (
    build_episode_prompt, build_lesson_plan_prompt,
    ALEX_PERSONA, SAM_PERSONA
)

# Part 4: Enhanced Audio Pipeline
from .audio_stitcher import AudioStitcher, AudioChunk, StitchConfig, create_silence
from .enhanced_audio_synthesizer import (
    EnhancedAudioSynthesizer, SynthesisConfig, SynthesisResult, SynthesisProgress
)
from .audio_coordinator import (
    AudioCoordinator, SynthesisJob, BatchResult, JobStatus, quick_synthesize
)

# Part 5: Session Management & Integration
from .tutor_session import (
    TutorSessionManager, TutorSessionData, LessonInfo, SessionStatus,
    get_manager, create_lesson_from_url
)

__all__ = [
    # Extractors
    'ContentExtractor',
    'ContentProcessor',
    'ProcessedContent',
    'ContentChunk',

    # Generators
    'PodcastGenerator',
    'AudioSynthesizer',

    # Models
    'DialogueTurn',
    'EpisodeScript',
    'EpisodeSegment',
    'LessonPlan',
    'Speaker',
    'SegmentType',
    'EmotionHint',

    # Formatters
    'ScriptFormatter',
    'format_for_polly',
    'generate_transcript',

    # Audio Pipeline (Part 4)
    'AudioStitcher',
    'AudioChunk',
    'StitchConfig',
    'create_silence',
    'EnhancedAudioSynthesizer',
    'SynthesisConfig',
    'SynthesisResult',
    'SynthesisProgress',
    'AudioCoordinator',
    'SynthesisJob',
    'BatchResult',
    'JobStatus',
    'quick_synthesize',

    # Session Management (Part 5)
    'TutorSessionManager',
    'TutorSessionData',
    'LessonInfo',
    'SessionStatus',
    'get_manager',
    'create_lesson_from_url',

    # Utilities
    'validate_script',
    'build_episode_prompt',
    'build_lesson_plan_prompt',
    'ALEX_PERSONA',
    'SAM_PERSONA'
]
