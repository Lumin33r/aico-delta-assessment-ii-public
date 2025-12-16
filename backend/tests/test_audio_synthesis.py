"""
Tests for Audio Synthesis Pipeline (Part 4)

Unit tests for:
- AudioStitcher
- EnhancedAudioSynthesizer
- AudioCoordinator
- SynthesisJob, BatchResult
"""

import pytest
import os
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.audio_stitcher import (
    AudioStitcher, AudioChunk, StitchConfig,
    create_silence, calculate_duration,
    PYDUB_AVAILABLE
)
from services.enhanced_audio_synthesizer import (
    EnhancedAudioSynthesizer, SynthesisConfig, SynthesisResult, SynthesisProgress,
    VOICE_CONFIG, VOICE_CONFIG_BY_NAME
)
from services.audio_coordinator import (
    AudioCoordinator, SynthesisJob, BatchResult, JobStatus, quick_synthesize
)
from services.dialogue_models import (
    DialogueTurn, EpisodeScript, EpisodeSegment,
    Speaker, SegmentType, EmotionHint
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_audio_chunk():
    """Create a sample AudioChunk for testing."""
    return AudioChunk(
        audio_bytes=b'\x00' * 1000,  # 1KB of zeros (mock audio)
        speaker='alex',
        voice_id='Matthew',
        duration_ms=500,
        segment_index=0,
        text="Hello, welcome to the show!"
    )


@pytest.fixture
def sample_episode_script():
    """Create a sample EpisodeScript for testing."""
    intro = EpisodeSegment(
        name="Introduction",
        segment_type=SegmentType.INTRO,
        turns=[
            DialogueTurn(
                speaker=Speaker.ALEX,
                text="Welcome to Tech Explained! I'm Alex.",
                segment_type=SegmentType.INTRO,
                emotion=EmotionHint.ENTHUSIASTIC
            ),
            DialogueTurn(
                speaker=Speaker.SAM,
                text="And I'm Sam! Today we're talking about Python.",
                segment_type=SegmentType.INTRO,
                emotion=EmotionHint.CURIOUS
            )
        ]
    )

    discussion = EpisodeSegment(
        name="Discussion",
        segment_type=SegmentType.DISCUSSION,
        turns=[
            DialogueTurn(
                speaker=Speaker.ALEX,
                text="Python is a versatile programming language.",
                segment_type=SegmentType.DISCUSSION,
                emotion=EmotionHint.THOUGHTFUL
            )
        ]
    )

    outro = EpisodeSegment(
        name="Outro",
        segment_type=SegmentType.OUTRO,
        turns=[
            DialogueTurn(
                speaker=Speaker.ALEX,
                text="Thanks for listening!",
                segment_type=SegmentType.OUTRO,
                emotion=EmotionHint.ENTHUSIASTIC
            )
        ]
    )

    return EpisodeScript(
        title="Python Basics",
        lesson_number=1,
        total_lessons=3,
        topic_description="Introduction to Python",
        key_concepts=["python", "programming"],
        segments=[intro, discussion, outro]
    )


@pytest.fixture
def mock_polly_response():
    """Create mock Polly response."""
    mock_stream = Mock()
    mock_stream.read.return_value = b'\x00' * 3000  # 3KB mock audio
    return {'AudioStream': mock_stream}


# =============================================================================
# AudioStitcher Tests
# =============================================================================

class TestStitchConfig:
    """Tests for StitchConfig dataclass."""

    def test_default_config(self):
        config = StitchConfig()

        assert config.pause_between_speakers == 600
        assert config.pause_same_speaker == 250
        assert config.output_format == "mp3"

    def test_custom_config(self):
        config = StitchConfig(
            pause_between_speakers=800,
            normalize_audio=False
        )

        assert config.pause_between_speakers == 800
        assert config.normalize_audio is False


class TestAudioChunk:
    """Tests for AudioChunk dataclass."""

    def test_audio_chunk_creation(self, sample_audio_chunk):
        assert sample_audio_chunk.speaker == 'alex'
        assert sample_audio_chunk.voice_id == 'Matthew'
        assert sample_audio_chunk.duration_ms == 500
        assert len(sample_audio_chunk.audio_bytes) == 1000


class TestAudioStitcher:
    """Tests for AudioStitcher class."""

    @pytest.fixture
    def stitcher(self):
        return AudioStitcher()

    def test_init(self, stitcher):
        assert stitcher.config is not None
        assert isinstance(stitcher.config, StitchConfig)

    def test_stitch_empty_list(self, stitcher):
        audio, duration = stitcher.stitch([])

        assert audio == b''
        assert duration == 0

    def test_stitch_simple(self, stitcher, sample_audio_chunk):
        """Test simple concatenation with mock chunks."""
        chunks = [sample_audio_chunk, sample_audio_chunk]

        audio, duration = stitcher._stitch_simple(chunks)

        assert len(audio) == 2000  # Two 1KB chunks
        assert duration == 1000  # 500ms + 500ms

    def test_calculate_pause_different_speakers(self, stitcher):
        pause = stitcher._calculate_pause(
            current_speaker='sam',
            last_speaker='alex',
            segment_changed=False,
            include_segment_pauses=True
        )

        assert pause == stitcher.config.pause_between_speakers

    def test_calculate_pause_same_speaker(self, stitcher):
        pause = stitcher._calculate_pause(
            current_speaker='alex',
            last_speaker='alex',
            segment_changed=False,
            include_segment_pauses=True
        )

        assert pause == stitcher.config.pause_same_speaker

    def test_calculate_pause_segment_change(self, stitcher):
        pause = stitcher._calculate_pause(
            current_speaker='alex',
            last_speaker='alex',
            segment_changed=True,
            include_segment_pauses=True
        )

        assert pause == stitcher.config.pause_segment_transition

    @pytest.mark.skipif(not PYDUB_AVAILABLE, reason="pydub/ffmpeg not available")
    def test_get_audio_info_basic(self, stitcher):
        """Test getting audio info structure (gracefully handles invalid audio)."""
        # Test with dummy bytes - should return info dict even if parsing fails
        info = stitcher.get_audio_info(b'\x00' * 3000)

        # The info dict should always be returned with pydub_available
        assert 'pydub_available' in info
        # May contain 'duration_ms' or 'error' depending on whether parsing succeeded
        assert 'duration_ms' in info or 'error' in info


class TestSilenceCreation:
    """Tests for silence creation utilities."""

    def test_create_silence_no_pydub(self):
        """Without pydub, should return empty bytes."""
        if not PYDUB_AVAILABLE:
            result = create_silence(1000)
            assert result == b''

    def test_calculate_duration(self):
        """Test duration estimation."""
        # 3000 bytes at ~3KB/s = ~1000ms
        duration = calculate_duration(b'\x00' * 3000)
        assert duration > 0


# =============================================================================
# EnhancedAudioSynthesizer Tests
# =============================================================================

class TestVoiceConfig:
    """Tests for voice configuration."""

    def test_voice_config_speakers(self):
        assert Speaker.ALEX in VOICE_CONFIG
        assert Speaker.SAM in VOICE_CONFIG

    def test_alex_voice(self):
        config = VOICE_CONFIG[Speaker.ALEX]

        assert config['voice_id'] == 'Matthew'
        assert config['engine'] == 'neural'
        assert config['language_code'] == 'en-US'

    def test_sam_voice(self):
        config = VOICE_CONFIG[Speaker.SAM]

        assert config['voice_id'] == 'Joanna'
        assert config['engine'] == 'neural'

    def test_voice_config_by_name(self):
        assert 'alex' in VOICE_CONFIG_BY_NAME
        assert 'sam' in VOICE_CONFIG_BY_NAME


class TestSynthesisConfig:
    """Tests for SynthesisConfig dataclass."""

    def test_default_config(self):
        config = SynthesisConfig()

        assert config.region == 'us-east-1'
        assert config.output_format == 'mp3'
        assert config.max_concurrent_requests == 3

    def test_custom_config(self):
        config = SynthesisConfig(
            region='us-west-2',
            bucket='custom-bucket',
            enable_caching=False
        )

        assert config.region == 'us-west-2'
        assert config.bucket == 'custom-bucket'
        assert config.enable_caching is False


class TestSynthesisResult:
    """Tests for SynthesisResult dataclass."""

    def test_result_creation(self):
        result = SynthesisResult(
            success=True,
            audio_url='http://example.com/audio.mp3',
            duration_seconds=120.5,
            segment_count=10
        )

        assert result.success is True
        assert result.duration_seconds == 120.5

    def test_result_to_dict(self):
        result = SynthesisResult(
            success=True,
            audio_url='http://example.com/audio.mp3',
            duration_seconds=60.0,
            segment_count=5,
            total_words=500,
            storage_type='s3'
        )

        d = result.to_dict()

        assert d['success'] is True
        assert d['audio_url'] == 'http://example.com/audio.mp3'
        assert d['storage_type'] == 's3'


class TestSynthesisProgress:
    """Tests for SynthesisProgress dataclass."""

    def test_progress_percent(self):
        progress = SynthesisProgress(
            total_segments=10,
            completed_segments=5
        )

        assert progress.percent_complete == 50.0

    def test_progress_percent_zero(self):
        progress = SynthesisProgress(total_segments=0)

        assert progress.percent_complete == 0.0


class TestEnhancedAudioSynthesizer:
    """Tests for EnhancedAudioSynthesizer class."""

    @pytest.fixture
    def synthesizer(self):
        return EnhancedAudioSynthesizer()

    def test_init(self, synthesizer):
        assert synthesizer.config is not None
        assert synthesizer.formatter is not None
        assert synthesizer.stitcher is not None

    def test_init_custom_config(self):
        config = SynthesisConfig(bucket='test-bucket')
        synth = EnhancedAudioSynthesizer(config=config)

        assert synth.config.bucket == 'test-bucket'

    @patch('services.enhanced_audio_synthesizer.boto3')
    def test_check_health_no_aws(self, mock_boto):
        """Test health check when AWS is not available."""
        synth = EnhancedAudioSynthesizer()
        synth._aws_available = False

        health = synth.check_health()

        assert health['aws_available'] is False
        assert health['polly'] is False

    def test_estimate_duration(self, synthesizer):
        # 6KB should be about 1000ms at our estimate
        duration = synthesizer._estimate_duration(b'\x00' * 6000)

        assert duration == 1000

    def test_estimate_duration_from_text(self, synthesizer):
        # 25 words at 2.5 wps = 10 seconds = 10000ms
        text = ' '.join(['word'] * 25)
        duration = synthesizer._estimate_duration_from_text(text)

        assert duration == 10000

    def test_get_cache_key(self, synthesizer):
        key1 = synthesizer._get_cache_key("hello", "Matthew")
        key2 = synthesizer._get_cache_key("hello", "Matthew")
        key3 = synthesizer._get_cache_key("hello", "Joanna")

        assert key1 == key2  # Same input, same key
        assert key1 != key3  # Different voice, different key

    def test_mock_synthesis(self, synthesizer, sample_episode_script):
        """Test mock synthesis when AWS is unavailable."""
        synthesizer._aws_available = False

        result = synthesizer._mock_synthesis(
            sample_episode_script,
            "test_session"
        )

        assert result.success is True
        assert result.storage_type == 'mock'
        assert 'mock' in result.audio_url.lower()

    def test_estimate_cost(self, synthesizer, sample_episode_script):
        cost = synthesizer.estimate_cost(sample_episode_script)

        assert 'total_characters' in cost
        assert 'neural_cost_usd' in cost
        assert cost['recommended'] == 'neural'


# =============================================================================
# AudioCoordinator Tests
# =============================================================================

class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_status_values(self):
        assert JobStatus.PENDING.value == 'pending'
        assert JobStatus.COMPLETED.value == 'completed'
        assert JobStatus.FAILED.value == 'failed'


class TestSynthesisJob:
    """Tests for SynthesisJob dataclass."""

    def test_job_creation(self):
        job = SynthesisJob(
            job_id='job_123',
            session_id='session_456',
            lesson_number=1
        )

        assert job.job_id == 'job_123'
        assert job.status == JobStatus.PENDING
        assert job.progress_percent == 0.0

    def test_job_to_dict(self):
        job = SynthesisJob(
            job_id='job_123',
            session_id='session_456',
            lesson_number=1,
            script_title='Test Episode'
        )

        d = job.to_dict()

        assert d['job_id'] == 'job_123'
        assert d['status'] == 'pending'
        assert d['script_title'] == 'Test Episode'


class TestBatchResult:
    """Tests for BatchResult dataclass."""

    def test_batch_result_creation(self):
        result = BatchResult(total_jobs=5)

        assert result.total_jobs == 5
        assert result.completed_jobs == 0
        assert result.failed_jobs == 0

    def test_batch_result_to_dict(self):
        result = BatchResult(
            total_jobs=3,
            completed_jobs=2,
            failed_jobs=1
        )

        d = result.to_dict()

        assert d['total_jobs'] == 3
        assert d['completed_jobs'] == 2


class TestAudioCoordinator:
    """Tests for AudioCoordinator class."""

    @pytest.fixture
    def coordinator(self):
        return AudioCoordinator()

    def test_init(self, coordinator):
        assert coordinator.synthesizer is not None
        assert coordinator.generator is not None
        assert coordinator.formatter is not None

    def test_init_custom_components(self):
        mock_synth = Mock()
        coord = AudioCoordinator(synthesizer=mock_synth)

        assert coord.synthesizer == mock_synth

    def test_add_progress_callback(self, coordinator):
        callback = Mock()
        coordinator.add_progress_callback(callback)

        assert callback in coordinator._progress_callbacks

    def test_notify_progress(self, coordinator):
        callback = Mock()
        coordinator.add_progress_callback(callback)

        job = SynthesisJob(
            job_id='test',
            session_id='session',
            lesson_number=1
        )

        coordinator._notify_progress(job)
        callback.assert_called_once_with(job)

    def test_extract_key_concepts(self, coordinator):
        content = """
        # Introduction
        This is about **Python** programming.
        We'll cover **variables** and **functions**.
        """

        concepts = coordinator._extract_key_concepts(content)

        assert len(concepts) <= 5
        assert 'Introduction' in concepts or 'Python' in concepts

    def test_get_session_jobs(self, coordinator):
        # Add some jobs
        job1 = SynthesisJob(job_id='j1', session_id='s1', lesson_number=1)
        job2 = SynthesisJob(job_id='j2', session_id='s1', lesson_number=2)
        job3 = SynthesisJob(job_id='j3', session_id='s2', lesson_number=1)

        coordinator._jobs['j1'] = job1
        coordinator._jobs['j2'] = job2
        coordinator._jobs['j3'] = job3

        session_jobs = coordinator.get_session_jobs('s1')

        assert len(session_jobs) == 2
        assert all(j.session_id == 's1' for j in session_jobs)

    def test_cleanup_old_jobs(self, coordinator):
        # Add an old completed job
        old_job = SynthesisJob(
            job_id='old_job',
            session_id='session',
            lesson_number=1,
            status=JobStatus.COMPLETED,
            completed_at=datetime.utcnow() - timedelta(hours=48)
        )
        coordinator._jobs['old_job'] = old_job

        # Add a recent job
        new_job = SynthesisJob(
            job_id='new_job',
            session_id='session',
            lesson_number=2,
            status=JobStatus.COMPLETED,
            completed_at=datetime.utcnow()
        )
        coordinator._jobs['new_job'] = new_job

        removed = coordinator.cleanup_old_jobs(max_age_hours=24)

        assert removed == 1
        assert 'old_job' not in coordinator._jobs
        assert 'new_job' in coordinator._jobs

    def test_estimate_batch_cost(self, coordinator, sample_episode_script):
        scripts = [sample_episode_script, sample_episode_script]

        estimate = coordinator.estimate_batch_cost(scripts)

        assert estimate['episode_count'] == 2
        assert 'estimated_cost_usd' in estimate
        assert 'cost_per_episode_usd' in estimate


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the audio pipeline."""

    def test_full_pipeline_mock(self, sample_episode_script):
        """Test full pipeline in mock mode (no AWS)."""
        coordinator = AudioCoordinator()
        coordinator.synthesizer._aws_available = False

        # Track progress
        progress_updates = []

        def track_progress(job):
            progress_updates.append(job.progress_percent)

        coordinator.add_progress_callback(track_progress)

        # Process episode
        job = coordinator.process_episode(
            script=sample_episode_script,
            session_id='test_session',
            upload_to_s3=False
        )

        # Verify job completed
        assert job.status == JobStatus.COMPLETED
        assert job.result is not None
        assert job.result.storage_type == 'mock'

    def test_synthesis_result_contains_metadata(self, sample_episode_script):
        """Test that synthesis result includes proper metadata."""
        synth = EnhancedAudioSynthesizer()
        synth._aws_available = False

        result = synth._mock_synthesis(sample_episode_script, 'session_123')

        assert 'title' in result.metadata
        assert 'lesson_number' in result.metadata
        assert result.metadata['title'] == 'Python Basics'


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
