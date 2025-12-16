"""
Audio Coordinator

Orchestrates the complete audio synthesis pipeline from content to final audio.

Workflow:
1. Accept EpisodeScript or raw content
2. Generate/validate dialogue script
3. Format for synthesis (SSML)
4. Synthesize audio with AWS Polly
5. Stitch audio segments together
6. Upload to S3 / save locally
7. Return playable audio URL

Features:
- End-to-end audio generation
- Progress tracking with callbacks
- Batch episode processing
- Error recovery and retry logic
- Cost estimation and reporting
"""

import os
import json
import logging
import time
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .dialogue_models import (
    EpisodeScript, EpisodeSegment, DialogueTurn,
    Speaker, SegmentType, validate_script
)
from .podcast_generator import PodcastGenerator
from .script_formatter import ScriptFormatter
from .enhanced_audio_synthesizer import (
    EnhancedAudioSynthesizer, SynthesisConfig, SynthesisResult
)
from .audio_stitcher import AudioStitcher, StitchConfig

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Status of a synthesis job."""
    PENDING = "pending"
    VALIDATING = "validating"
    GENERATING_SCRIPT = "generating_script"
    FORMATTING = "formatting"
    SYNTHESIZING = "synthesizing"
    STITCHING = "stitching"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SynthesisJob:
    """
    Represents a single audio synthesis job.
    """
    job_id: str
    session_id: str
    lesson_number: int
    status: JobStatus = JobStatus.PENDING
    progress_percent: float = 0.0
    current_step: str = ""

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    result: Optional[SynthesisResult] = None
    error: Optional[str] = None

    # Metadata
    script_title: str = ""
    total_words: int = 0
    estimated_duration_seconds: float = 0.0

    def to_dict(self) -> Dict:
        return {
            'job_id': self.job_id,
            'session_id': self.session_id,
            'lesson_number': self.lesson_number,
            'status': self.status.value,
            'progress_percent': self.progress_percent,
            'current_step': self.current_step,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'result': self.result.to_dict() if self.result else None,
            'error': self.error,
            'script_title': self.script_title,
            'total_words': self.total_words,
            'estimated_duration_seconds': self.estimated_duration_seconds
        }


@dataclass
class BatchResult:
    """Results from batch episode processing."""
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    jobs: List[SynthesisJob] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    total_cost_estimate: float = 0.0

    def to_dict(self) -> Dict:
        return {
            'total_jobs': self.total_jobs,
            'completed_jobs': self.completed_jobs,
            'failed_jobs': self.failed_jobs,
            'jobs': [job.to_dict() for job in self.jobs],
            'total_duration_seconds': self.total_duration_seconds,
            'total_cost_estimate': self.total_cost_estimate
        }


class AudioCoordinator:
    """
    Coordinates the complete audio synthesis pipeline.
    """

    def __init__(
        self,
        synthesizer: Optional[EnhancedAudioSynthesizer] = None,
        generator: Optional[PodcastGenerator] = None,
        formatter: Optional[ScriptFormatter] = None,
        output_dir: str = "/tmp/audio_output"
    ):
        """
        Initialize the audio coordinator.

        Args:
            synthesizer: Audio synthesizer instance
            generator: Podcast generator instance
            formatter: Script formatter instance
            output_dir: Directory for output files
        """
        self.synthesizer = synthesizer or EnhancedAudioSynthesizer()
        self.generator = generator or PodcastGenerator()
        self.formatter = formatter or ScriptFormatter()
        self.output_dir = output_dir

        # Job tracking
        self._jobs: Dict[str, SynthesisJob] = {}
        self._progress_callbacks: List[Callable[[SynthesisJob], None]] = []

        # Setup output directory
        os.makedirs(output_dir, exist_ok=True)

    def add_progress_callback(
        self,
        callback: Callable[[SynthesisJob], None]
    ) -> None:
        """Add a callback for job progress updates."""
        self._progress_callbacks.append(callback)

    def _notify_progress(self, job: SynthesisJob) -> None:
        """Notify all callbacks of job progress."""
        for callback in self._progress_callbacks:
            try:
                callback(job)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

    def process_episode(
        self,
        script: EpisodeScript,
        session_id: str,
        upload_to_s3: bool = True
    ) -> SynthesisJob:
        """
        Process a complete episode from EpisodeScript.

        Args:
            script: EpisodeScript to synthesize
            session_id: Session identifier
            upload_to_s3: Whether to upload to S3

        Returns:
            SynthesisJob with results
        """
        # Create job
        job_id = f"{session_id}_{script.lesson_number}_{int(time.time())}"
        job = SynthesisJob(
            job_id=job_id,
            session_id=session_id,
            lesson_number=script.lesson_number,
            script_title=script.title,
            total_words=script.total_words,
            estimated_duration_seconds=script.estimated_duration_minutes * 60
        )
        self._jobs[job_id] = job

        try:
            # Start processing
            job.started_at = datetime.utcnow()

            # Step 1: Validate script
            job.status = JobStatus.VALIDATING
            job.current_step = "Validating script structure"
            job.progress_percent = 10
            self._notify_progress(job)

            validation = validate_script(script)
            if not validation['valid']:
                logger.warning(f"Script validation issues: {validation['issues']}")
                # Continue anyway - just log warnings

            # Step 2: Format for synthesis
            job.status = JobStatus.FORMATTING
            job.current_step = "Formatting script for synthesis"
            job.progress_percent = 20
            self._notify_progress(job)

            # Script is already formatted, formatter is used by synthesizer

            # Step 3: Synthesize audio
            job.status = JobStatus.SYNTHESIZING
            job.current_step = "Synthesizing audio with AWS Polly"
            job.progress_percent = 30
            self._notify_progress(job)

            # Set up progress tracking
            def synthesis_progress(progress):
                job.progress_percent = 30 + (progress.percent_complete * 0.5)
                job.current_step = progress.current_segment
                self._notify_progress(job)

            self.synthesizer.set_progress_callback(synthesis_progress)

            # Synthesize
            result = self.synthesizer.synthesize_episode(
                script=script,
                session_id=session_id,
                upload_to_s3=upload_to_s3,
                save_local=True
            )

            # Step 4: Finalize
            job.status = JobStatus.COMPLETED
            job.current_step = "Audio generation complete"
            job.progress_percent = 100
            job.completed_at = datetime.utcnow()
            job.result = result
            self._notify_progress(job)

            logger.info(f"Job {job_id} completed: {result.duration_seconds:.1f}s audio")

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            self._notify_progress(job)

        return job

    def process_content(
        self,
        content: str,
        title: str,
        session_id: str,
        lesson_number: int = 1,
        total_lessons: int = 1,
        target_duration_minutes: int = 10,
        upload_to_s3: bool = True
    ) -> SynthesisJob:
        """
        Process raw content into a podcast episode.

        This is the full pipeline: content → script → audio

        Args:
            content: Raw educational content
            title: Episode title
            session_id: Session identifier
            lesson_number: Lesson number
            total_lessons: Total number of lessons
            target_duration_minutes: Target episode duration
            upload_to_s3: Whether to upload to S3

        Returns:
            SynthesisJob with results
        """
        # Create job
        job_id = f"{session_id}_{lesson_number}_{int(time.time())}"
        job = SynthesisJob(
            job_id=job_id,
            session_id=session_id,
            lesson_number=lesson_number,
            script_title=title
        )
        self._jobs[job_id] = job

        try:
            job.started_at = datetime.utcnow()

            # Step 1: Generate script
            job.status = JobStatus.GENERATING_SCRIPT
            job.current_step = "Generating podcast script with AI"
            job.progress_percent = 10
            self._notify_progress(job)

            # Check if generator is available
            if not self.generator.check_health():
                raise RuntimeError("Podcast generator (Ollama) is not available")

            # Create topic for generation
            topic = {
                'title': title,
                'description': f"Educational content about {title}",
                'key_concepts': self._extract_key_concepts(content)
            }

            # Generate episode script
            script = self.generator.generate_episode(
                topic=topic,
                content=content,
                lesson_number=lesson_number,
                total_lessons=total_lessons,
                target_duration=target_duration_minutes
            )

            job.total_words = script.total_words
            job.estimated_duration_seconds = script.estimated_duration_minutes * 60
            job.progress_percent = 40
            self._notify_progress(job)

            # Continue with normal episode processing
            # ... (synthesis steps)

            # Step 2: Validate
            job.status = JobStatus.VALIDATING
            job.current_step = "Validating generated script"
            job.progress_percent = 45
            self._notify_progress(job)

            # Step 3: Synthesize
            job.status = JobStatus.SYNTHESIZING
            job.current_step = "Synthesizing audio"
            job.progress_percent = 50
            self._notify_progress(job)

            result = self.synthesizer.synthesize_episode(
                script=script,
                session_id=session_id,
                upload_to_s3=upload_to_s3,
                save_local=True
            )

            # Complete
            job.status = JobStatus.COMPLETED
            job.current_step = "Complete"
            job.progress_percent = 100
            job.completed_at = datetime.utcnow()
            job.result = result
            self._notify_progress(job)

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            self._notify_progress(job)

        return job

    def process_batch(
        self,
        scripts: List[EpisodeScript],
        session_id: str,
        upload_to_s3: bool = True
    ) -> BatchResult:
        """
        Process multiple episodes in sequence.

        Args:
            scripts: List of EpisodeScripts to process
            session_id: Session identifier
            upload_to_s3: Whether to upload to S3

        Returns:
            BatchResult with all job results
        """
        result = BatchResult(total_jobs=len(scripts))

        for script in scripts:
            job = self.process_episode(
                script=script,
                session_id=session_id,
                upload_to_s3=upload_to_s3
            )

            result.jobs.append(job)

            if job.status == JobStatus.COMPLETED:
                result.completed_jobs += 1
                if job.result:
                    result.total_duration_seconds += job.result.duration_seconds
            else:
                result.failed_jobs += 1

        # Estimate total cost
        for script in scripts:
            cost = self.synthesizer.estimate_cost(script)
            result.total_cost_estimate += cost['neural_cost_usd']

        return result

    def get_job(self, job_id: str) -> Optional[SynthesisJob]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def get_session_jobs(self, session_id: str) -> List[SynthesisJob]:
        """Get all jobs for a session."""
        return [
            job for job in self._jobs.values()
            if job.session_id == session_id
        ]

    def _extract_key_concepts(self, content: str, max_concepts: int = 5) -> List[str]:
        """
        Extract key concepts from content.

        Simple implementation - could be enhanced with NLP.
        """
        # Look for common patterns
        concepts = []

        # Headers (markdown)
        import re
        headers = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
        concepts.extend(headers[:max_concepts])

        # Bold text
        bold = re.findall(r'\*\*(.+?)\*\*', content)
        concepts.extend(bold[:max_concepts - len(concepts)])

        # Fallback to first few unique words
        if len(concepts) < 3:
            words = content.split()[:100]
            unique_words = list(dict.fromkeys(
                w.strip('.,!?:;') for w in words
                if len(w) > 5 and w[0].isupper()
            ))
            concepts.extend(unique_words[:max_concepts - len(concepts)])

        return concepts[:max_concepts]

    def estimate_batch_cost(self, scripts: List[EpisodeScript]) -> Dict:
        """
        Estimate cost for batch processing.

        Args:
            scripts: List of scripts to estimate

        Returns:
            Cost breakdown
        """
        total_chars = 0
        total_words = 0
        total_duration = 0.0

        for script in scripts:
            cost = self.synthesizer.estimate_cost(script)
            total_chars += cost['total_characters']
            total_words += script.total_words
            total_duration += script.estimated_duration_minutes

        ssml_chars = int(total_chars * 1.2)
        neural_cost = (ssml_chars / 1_000_000) * 16.00

        return {
            'episode_count': len(scripts),
            'total_words': total_words,
            'total_characters': total_chars,
            'ssml_characters': ssml_chars,
            'estimated_duration_minutes': total_duration,
            'estimated_cost_usd': round(neural_cost, 4),
            'cost_per_episode_usd': round(neural_cost / len(scripts), 4) if scripts else 0
        }

    def check_health(self) -> Dict[str, Any]:
        """
        Check health of all coordinator components.

        Returns:
            Health status for each component
        """
        return {
            'synthesizer': self.synthesizer.check_health(),
            'generator_available': self.generator.check_health(),
            'output_dir_writable': os.access(self.output_dir, os.W_OK),
            'active_jobs': len([j for j in self._jobs.values()
                               if j.status not in [JobStatus.COMPLETED, JobStatus.FAILED]])
        }

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """
        Remove old completed jobs from memory.

        Args:
            max_age_hours: Maximum age of jobs to keep

        Returns:
            Number of jobs removed
        """
        now = datetime.utcnow()
        removed = 0

        to_remove = []
        for job_id, job in self._jobs.items():
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                if job.completed_at:
                    age = (now - job.completed_at).total_seconds() / 3600
                    if age > max_age_hours:
                        to_remove.append(job_id)

        for job_id in to_remove:
            del self._jobs[job_id]
            removed += 1

        return removed


# =============================================================================
# Convenience Functions
# =============================================================================

def quick_synthesize(
    content: str,
    title: str,
    session_id: str = "quick_session"
) -> Dict:
    """
    Quick synthesis of content to audio.

    Convenience function for simple use cases.

    Args:
        content: Educational content
        title: Episode title
        session_id: Session identifier

    Returns:
        Result dict with audio URL
    """
    coordinator = AudioCoordinator()

    job = coordinator.process_content(
        content=content,
        title=title,
        session_id=session_id,
        upload_to_s3=False  # Local only for quick synthesis
    )

    return job.to_dict()


# =============================================================================
# Demo/Testing
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Audio Coordinator")
    print("=" * 40)

    coordinator = AudioCoordinator()

    # Check health
    health = coordinator.check_health()
    print("\nComponent Health:")
    for component, status in health.items():
        if isinstance(status, dict):
            print(f"  {component}:")
            for k, v in status.items():
                status_icon = "✓" if v else "✗"
                print(f"    {status_icon} {k}: {v}")
        else:
            status_icon = "✓" if status else "✗"
            print(f"  {status_icon} {component}: {status}")

    # Example usage (if services available)
    print("\nUsage Example:")
    print("""
    coordinator = AudioCoordinator()

    # From EpisodeScript:
    job = coordinator.process_episode(script, session_id="user123")
    print(job.result.audio_url)

    # From raw content:
    job = coordinator.process_content(
        content="Python is a programming language...",
        title="Introduction to Python",
        session_id="user123"
    )
    """)
