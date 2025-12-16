"""
Enhanced Audio Synthesizer

Production-ready audio synthesis for podcast generation using AWS Polly
with support for structured EpisodeScript models.

Features:
- Integration with dialogue models (EpisodeScript, DialogueTurn)
- SSML formatting from ScriptFormatter
- Multi-voice synthesis with natural transitions
- Progress tracking and callbacks
- S3 upload with presigned URLs
- Local file caching
- Retry logic and error handling
"""

import io
import os
import time
import logging
import hashlib
import json
from typing import Dict, List, Optional, Tuple, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from .dialogue_models import (
    EpisodeScript, EpisodeSegment, DialogueTurn,
    Speaker, SegmentType, EmotionHint
)
from .script_formatter import ScriptFormatter, SSMLConfig
from .audio_stitcher import AudioStitcher, AudioChunk, StitchConfig

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class SynthesisConfig:
    """Configuration for audio synthesis."""
    # AWS settings
    region: str = "us-east-1"
    bucket: str = "ai-tutor-audio"

    # Audio settings
    output_format: str = "mp3"
    sample_rate: str = "24000"
    engine: str = "neural"

    # Processing settings
    max_concurrent_requests: int = 3
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0

    # Caching
    enable_caching: bool = True
    cache_dir: str = "/tmp/audio_cache"

    # Limits
    max_text_length: int = 2900  # Polly limit is 3000


@dataclass
class SynthesisProgress:
    """Tracks synthesis progress for callbacks."""
    total_segments: int = 0
    completed_segments: int = 0
    failed_segments: int = 0
    current_segment: str = ""
    elapsed_seconds: float = 0.0
    estimated_remaining: float = 0.0

    @property
    def percent_complete(self) -> float:
        if self.total_segments == 0:
            return 0.0
        return (self.completed_segments / self.total_segments) * 100


@dataclass
class SynthesisResult:
    """Result of audio synthesis."""
    success: bool
    audio_url: str = ""
    s3_key: str = ""
    local_path: str = ""
    duration_seconds: float = 0.0
    segment_count: int = 0
    total_words: int = 0
    storage_type: str = "s3"  # s3, local, mock
    metadata: Dict = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'success': self.success,
            'audio_url': self.audio_url,
            's3_key': self.s3_key,
            'duration_seconds': self.duration_seconds,
            'segment_count': self.segment_count,
            'total_words': self.total_words,
            'storage_type': self.storage_type,
            'metadata': self.metadata,
            'error': self.error
        }


# =============================================================================
# Voice Configuration
# =============================================================================

VOICE_CONFIG = {
    Speaker.ALEX: {
        'voice_id': 'Matthew',
        'engine': 'neural',
        'language_code': 'en-US',
        'description': 'Expert host - warm, professional, knowledgeable'
    },
    Speaker.SAM: {
        'voice_id': 'Joanna',
        'engine': 'neural',
        'language_code': 'en-US',
        'description': 'Co-host - friendly, curious, engaging'
    }
}

# Also support string lookup
VOICE_CONFIG_BY_NAME = {
    'alex': VOICE_CONFIG[Speaker.ALEX],
    'sam': VOICE_CONFIG[Speaker.SAM]
}


# =============================================================================
# Enhanced Audio Synthesizer
# =============================================================================

class EnhancedAudioSynthesizer:
    """
    Production-ready audio synthesizer with EpisodeScript support.
    """

    def __init__(
        self,
        config: Optional[SynthesisConfig] = None,
        formatter: Optional[ScriptFormatter] = None,
        stitcher: Optional[AudioStitcher] = None
    ):
        """
        Initialize the enhanced synthesizer.

        Args:
            config: Synthesis configuration
            formatter: Script formatter for SSML
            stitcher: Audio stitcher for combining segments
        """
        self.config = config or SynthesisConfig()
        self.formatter = formatter or ScriptFormatter()
        self.stitcher = stitcher or AudioStitcher()

        # Initialize AWS clients
        try:
            self.polly = boto3.client('polly', region_name=self.config.region)
            self.s3 = boto3.client('s3', region_name=self.config.region)
            self._aws_available = True
        except NoCredentialsError:
            logger.warning("AWS credentials not found - using mock mode")
            self._aws_available = False
            self.polly = None
            self.s3 = None

        # Setup cache directory
        if self.config.enable_caching:
            os.makedirs(self.config.cache_dir, exist_ok=True)

        # Progress callback
        self._progress_callback: Optional[Callable[[SynthesisProgress], None]] = None

    def set_progress_callback(
        self,
        callback: Callable[[SynthesisProgress], None]
    ) -> None:
        """Set callback for progress updates during synthesis."""
        self._progress_callback = callback

    def check_health(self) -> Dict[str, Any]:
        """
        Check health of synthesis services.

        Returns:
            Health status dict
        """
        result = {
            'polly': False,
            's3': False,
            'aws_available': self._aws_available,
            'cache_enabled': self.config.enable_caching,
            'pydub_available': self.stitcher._pydub_available
        }

        if not self._aws_available:
            return result

        # Check Polly
        try:
            self.polly.describe_voices(LanguageCode='en-US')
            result['polly'] = True
        except Exception as e:
            result['polly_error'] = str(e)

        # Check S3 bucket
        try:
            self.s3.head_bucket(Bucket=self.config.bucket)
            result['s3'] = True
        except Exception as e:
            result['s3_error'] = str(e)

        return result

    def synthesize_episode(
        self,
        script: EpisodeScript,
        session_id: str,
        upload_to_s3: bool = True,
        save_local: bool = True
    ) -> SynthesisResult:
        """
        Synthesize a complete podcast episode from an EpisodeScript.

        Args:
            script: EpisodeScript with structured dialogue
            session_id: Session identifier for storage
            upload_to_s3: Whether to upload to S3
            save_local: Whether to save locally

        Returns:
            SynthesisResult with audio URL and metadata
        """
        start_time = time.time()

        if not self._aws_available:
            return self._mock_synthesis(script, session_id)

        logger.info(f"Synthesizing episode: {script.title}")
        logger.info(f"  Segments: {len(script.segments)}, Turns: {len(script.all_turns)}")

        # Initialize progress
        progress = SynthesisProgress(
            total_segments=len(script.all_turns)
        )

        # Format script for synthesis
        synthesis_chunks = self.formatter.format_for_synthesis(script)

        # Synthesize each chunk
        audio_chunks: List[AudioChunk] = []
        segment_idx = 0

        for chunk in synthesis_chunks:
            try:
                # Update progress
                progress.current_segment = f"Synthesizing: {chunk.get('speaker', 'unknown')}"
                self._report_progress(progress)

                # Get voice configuration
                speaker = chunk.get('speaker', 'alex')
                voice_config = VOICE_CONFIG_BY_NAME.get(speaker, VOICE_CONFIG_BY_NAME['alex'])

                # Check cache first
                cache_key = self._get_cache_key(chunk['ssml'], voice_config['voice_id'])
                cached_audio = self._get_from_cache(cache_key)

                if cached_audio:
                    audio_bytes = cached_audio
                    duration_ms = self._estimate_duration(audio_bytes)
                else:
                    # Synthesize with Polly
                    audio_bytes, duration_ms = self._synthesize_ssml(
                        ssml=chunk['ssml'],
                        voice_id=voice_config['voice_id'],
                        engine=voice_config['engine']
                    )

                    # Cache the result
                    self._save_to_cache(cache_key, audio_bytes)

                # Create audio chunk
                audio_chunk = AudioChunk(
                    audio_bytes=audio_bytes,
                    speaker=speaker,
                    voice_id=voice_config['voice_id'],
                    duration_ms=duration_ms,
                    segment_index=segment_idx,
                    text=str(chunk.get('original_texts', ''))[:100]
                )
                audio_chunks.append(audio_chunk)

                progress.completed_segments += 1
                segment_idx += 1

            except Exception as e:
                logger.error(f"Synthesis failed for chunk: {e}")
                progress.failed_segments += 1

        # Stitch audio together
        logger.info(f"Stitching {len(audio_chunks)} audio chunks...")
        combined_audio, total_duration_ms = self.stitcher.stitch(audio_chunks)

        # Calculate elapsed time
        elapsed = time.time() - start_time
        progress.elapsed_seconds = elapsed
        self._report_progress(progress)

        # Prepare result
        result = SynthesisResult(
            success=True,
            duration_seconds=total_duration_ms / 1000,
            segment_count=len(audio_chunks),
            total_words=script.total_words,
            metadata={
                'title': script.title,
                'lesson_number': script.lesson_number,
                'total_lessons': script.total_lessons,
                'synthesis_time_seconds': elapsed,
                'alex_words': script.alex_words,
                'sam_words': script.sam_words
            }
        )

        # Save locally
        if save_local:
            local_path = self._save_local(
                combined_audio,
                session_id,
                script.lesson_number
            )
            result.local_path = local_path

        # Upload to S3
        if upload_to_s3 and self._aws_available:
            try:
                s3_key = self._upload_to_s3(
                    combined_audio,
                    session_id,
                    script.lesson_number,
                    script.title
                )
                result.s3_key = s3_key
                result.audio_url = self.get_presigned_url(s3_key)
                result.storage_type = 's3'
            except Exception as e:
                logger.error(f"S3 upload failed: {e}")
                result.storage_type = 'local'
                result.audio_url = f"file://{result.local_path}"
        else:
            result.storage_type = 'local'
            result.audio_url = f"file://{result.local_path}"

        logger.info(f"Episode synthesis complete: {result.duration_seconds:.1f}s")
        return result

    def synthesize_turn(
        self,
        turn: DialogueTurn,
        use_ssml: bool = True
    ) -> Tuple[bytes, int]:
        """
        Synthesize a single dialogue turn.

        Args:
            turn: DialogueTurn to synthesize
            use_ssml: Whether to use SSML formatting

        Returns:
            Tuple of (audio_bytes, duration_ms)
        """
        if not self._aws_available:
            return b'', self._estimate_duration_from_text(turn.text)

        voice_config = VOICE_CONFIG.get(turn.speaker, VOICE_CONFIG[Speaker.ALEX])

        if use_ssml:
            ssml = self.formatter._format_turn_ssml(turn)
            return self._synthesize_ssml(
                ssml=ssml,
                voice_id=voice_config['voice_id'],
                engine=voice_config['engine']
            )
        else:
            return self._synthesize_text(
                text=turn.text,
                voice_id=voice_config['voice_id'],
                engine=voice_config['engine']
            )

    def _synthesize_ssml(
        self,
        ssml: str,
        voice_id: str,
        engine: str = "neural"
    ) -> Tuple[bytes, int]:
        """
        Synthesize SSML text using Polly.

        Args:
            ssml: SSML-formatted text
            voice_id: Polly voice ID
            engine: Synthesis engine

        Returns:
            Tuple of (audio_bytes, duration_ms)
        """
        for attempt in range(self.config.retry_attempts):
            try:
                response = self.polly.synthesize_speech(
                    Engine=engine,
                    LanguageCode='en-US',
                    OutputFormat=self.config.output_format,
                    SampleRate=self.config.sample_rate,
                    Text=ssml,
                    TextType='ssml',
                    VoiceId=voice_id
                )

                audio_bytes = response['AudioStream'].read()
                duration_ms = self._estimate_duration(audio_bytes)

                return audio_bytes, duration_ms

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')

                if error_code == 'ThrottlingException' and attempt < self.config.retry_attempts - 1:
                    time.sleep(self.config.retry_delay_seconds * (attempt + 1))
                    continue

                raise

        raise RuntimeError("Max retry attempts exceeded")

    def _synthesize_text(
        self,
        text: str,
        voice_id: str,
        engine: str = "neural"
    ) -> Tuple[bytes, int]:
        """
        Synthesize plain text using Polly.

        Args:
            text: Plain text to synthesize
            voice_id: Polly voice ID
            engine: Synthesis engine

        Returns:
            Tuple of (audio_bytes, duration_ms)
        """
        response = self.polly.synthesize_speech(
            Engine=engine,
            LanguageCode='en-US',
            OutputFormat=self.config.output_format,
            SampleRate=self.config.sample_rate,
            Text=text,
            TextType='text',
            VoiceId=voice_id
        )

        audio_bytes = response['AudioStream'].read()
        duration_ms = self._estimate_duration(audio_bytes)

        return audio_bytes, duration_ms

    def _estimate_duration(self, audio_bytes: bytes) -> int:
        """Estimate audio duration from byte size."""
        # MP3 at 24kHz, 48kbps ~= 6KB per second
        return int((len(audio_bytes) / 6000) * 1000)

    def _estimate_duration_from_text(self, text: str) -> int:
        """Estimate duration from text word count."""
        words = len(text.split())
        # Average speaking rate: 2.5 words per second
        return int((words / 2.5) * 1000)

    # =========================================================================
    # Caching
    # =========================================================================

    def _get_cache_key(self, text: str, voice_id: str) -> str:
        """Generate cache key for text/voice combination."""
        content = f"{voice_id}:{text}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[bytes]:
        """Get audio from cache if available."""
        if not self.config.enable_caching:
            return None

        cache_path = os.path.join(self.config.cache_dir, f"{cache_key}.mp3")

        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    return f.read()
            except Exception:
                pass

        return None

    def _save_to_cache(self, cache_key: str, audio_bytes: bytes) -> None:
        """Save audio to cache."""
        if not self.config.enable_caching:
            return

        try:
            cache_path = os.path.join(self.config.cache_dir, f"{cache_key}.mp3")
            with open(cache_path, 'wb') as f:
                f.write(audio_bytes)
        except Exception as e:
            logger.warning(f"Failed to cache audio: {e}")

    def clear_cache(self) -> int:
        """Clear audio cache. Returns number of files deleted."""
        if not os.path.exists(self.config.cache_dir):
            return 0

        count = 0
        for filename in os.listdir(self.config.cache_dir):
            if filename.endswith('.mp3'):
                try:
                    os.remove(os.path.join(self.config.cache_dir, filename))
                    count += 1
                except Exception:
                    pass

        return count

    # =========================================================================
    # Storage
    # =========================================================================

    def _save_local(
        self,
        audio_bytes: bytes,
        session_id: str,
        lesson_num: int
    ) -> str:
        """Save audio to local storage."""
        local_dir = os.path.join(self.config.cache_dir, session_id)
        os.makedirs(local_dir, exist_ok=True)

        local_path = os.path.join(local_dir, f"lesson_{lesson_num}.mp3")

        with open(local_path, 'wb') as f:
            f.write(audio_bytes)

        return local_path

    def _upload_to_s3(
        self,
        audio_bytes: bytes,
        session_id: str,
        lesson_num: int,
        title: str
    ) -> str:
        """Upload audio to S3."""
        s3_key = f"lessons/{session_id}/lesson_{lesson_num}.mp3"

        self.s3.put_object(
            Bucket=self.config.bucket,
            Key=s3_key,
            Body=audio_bytes,
            ContentType='audio/mpeg',
            Metadata={
                'session_id': session_id,
                'lesson_num': str(lesson_num),
                'title': title[:256],  # Metadata value limit
                'generated_at': datetime.utcnow().isoformat()
            }
        )

        logger.info(f"Uploaded to s3://{self.config.bucket}/{s3_key}")
        return s3_key

    def get_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600
    ) -> str:
        """Generate presigned URL for S3 object."""
        if not self._aws_available:
            return f"http://localhost:8000/mock-audio/{s3_key}"

        return self.s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.config.bucket,
                'Key': s3_key
            },
            ExpiresIn=expiration
        )

    # =========================================================================
    # Progress Reporting
    # =========================================================================

    def _report_progress(self, progress: SynthesisProgress) -> None:
        """Report progress via callback if set."""
        if self._progress_callback:
            try:
                self._progress_callback(progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

    # =========================================================================
    # Mock Mode
    # =========================================================================

    def _mock_synthesis(
        self,
        script: EpisodeScript,
        session_id: str
    ) -> SynthesisResult:
        """Generate mock result for development without AWS."""
        duration = script.estimated_duration_minutes * 60

        return SynthesisResult(
            success=True,
            audio_url=f"http://localhost:8000/mock-audio/{session_id}/{script.lesson_number}",
            duration_seconds=duration,
            segment_count=len(script.all_turns),
            total_words=script.total_words,
            storage_type='mock',
            metadata={
                'title': script.title,
                'lesson_number': script.lesson_number,
                'note': 'Mock mode - AWS credentials not configured'
            }
        )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def list_voices(self, language: str = 'en-US') -> List[Dict]:
        """List available Polly voices."""
        if not self._aws_available:
            return []

        try:
            response = self.polly.describe_voices(
                Engine='neural',
                LanguageCode=language
            )

            return [
                {
                    'id': voice['Id'],
                    'name': voice['Name'],
                    'gender': voice['Gender'],
                    'language': voice['LanguageName']
                }
                for voice in response.get('Voices', [])
            ]
        except Exception as e:
            logger.error(f"Failed to list voices: {e}")
            return []

    def estimate_cost(self, script: EpisodeScript) -> Dict:
        """
        Estimate AWS Polly cost for synthesizing a script.

        Neural voices: $16.00 per 1 million characters
        Standard voices: $4.00 per 1 million characters
        """
        total_chars = sum(len(turn.text) for turn in script.all_turns)

        # Add SSML overhead (~20%)
        ssml_chars = int(total_chars * 1.2)

        neural_cost = (ssml_chars / 1_000_000) * 16.00
        standard_cost = (ssml_chars / 1_000_000) * 4.00

        return {
            'total_characters': total_chars,
            'ssml_characters': ssml_chars,
            'neural_cost_usd': round(neural_cost, 4),
            'standard_cost_usd': round(standard_cost, 4),
            'recommended': 'neural'
        }


# =============================================================================
# Demo/Testing
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    synth = EnhancedAudioSynthesizer()

    print("Enhanced Audio Synthesizer")
    print("=" * 40)

    health = synth.check_health()
    print(f"\nHealth Check:")
    for key, value in health.items():
        status = "✓" if value else "✗"
        print(f"  {status} {key}: {value}")

    if health['polly']:
        voices = synth.list_voices()
        print(f"\nAvailable Neural Voices: {len(voices)}")
        for voice in voices[:5]:
            print(f"  - {voice['id']}: {voice['name']} ({voice['gender']})")

    print("\nVoice Configuration:")
    for speaker, config in VOICE_CONFIG.items():
        print(f"  {speaker.display_name}: {config['voice_id']} ({config['description']})")
