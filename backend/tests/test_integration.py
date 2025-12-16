"""
Integration Tests for AI Personal Tutor (Part 5)

End-to-end tests covering:
- TutorSessionManager full workflow
- API v2 endpoints
- Complete pipeline: URL → Content → Script → Audio
"""

import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import uuid

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.tutor_session import (
    TutorSessionManager, TutorSessionData, LessonInfo, SessionStatus,
    get_manager, create_lesson_from_url
)
from services.content_extractor import ContentExtractor
from services.content_processor import ContentProcessor, ProcessedContent
from services.podcast_generator import PodcastGenerator
from services.dialogue_models import (
    EpisodeScript, EpisodeSegment, DialogueTurn,
    Speaker, SegmentType, EmotionHint
)
from services.enhanced_audio_synthesizer import EnhancedAudioSynthesizer, SynthesisResult
from services.audio_coordinator import AudioCoordinator


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_raw_content():
    """Sample raw content from extraction."""
    return {
        'url': 'https://example.com/python-basics',
        'title': 'Python Basics Tutorial',
        'text': '''
        Python is a high-level programming language known for its simplicity.

        Variables and Data Types:
        Python supports integers, floats, strings, and boolean types.
        Variables are dynamically typed.

        Control Flow:
        Python uses if/elif/else for conditional logic.
        ''',
        'metadata': {
            'word_count': 50,
        }
    }


@pytest.fixture
def sample_processed_content():
    """Sample ProcessedContent object."""
    # Use Mock to avoid complex dataclass setup
    mock_content = Mock(spec=ProcessedContent)
    mock_content.title = 'Python Basics Tutorial'
    mock_content.url = 'https://example.com/python-basics'
    mock_content.summary = 'A guide to Python basics'
    mock_content.chunks = ['chunk1', 'chunk2']
    mock_content.topics = ['Python', 'Variables', 'Control Flow']
    mock_content.key_concepts = ['dynamic typing', 'conditionals']
    mock_content.total_words = 50
    mock_content.reading_time_minutes = 1
    mock_content.structure = {}
    mock_content.metadata = {}
    return mock_content


@pytest.fixture
def sample_lesson_topics():
    """Sample lesson plan from generator."""
    return [
        {
            'title': 'Getting Started with Python',
            'description': 'Introduction to Python and basic data types',
            'key_concepts': ['Python overview', 'Variables']
        },
        {
            'title': 'Control Flow in Python',
            'description': 'Learn about conditionals and loops',
            'key_concepts': ['If statements', 'Loops']
        },
        {
            'title': 'Functions and Organization',
            'description': 'Creating reusable code with functions',
            'key_concepts': ['Functions', 'Parameters']
        }
    ]


@pytest.fixture
def sample_episode_script():
    """Sample episode script for a lesson."""
    intro = EpisodeSegment(
        name="Introduction",
        segment_type=SegmentType.INTRO,
        turns=[
            DialogueTurn(
                speaker=Speaker.ALEX,
                text="Welcome to Python Basics!",
                segment_type=SegmentType.INTRO,
                emotion=EmotionHint.ENTHUSIASTIC
            )
        ]
    )

    return EpisodeScript(
        title="Python Basics - Lesson 1",
        topic="Getting Started with Python",
        segments=[intro],
        total_turns=1,
        estimated_duration_minutes=10.0,
        metadata={}
    )


@pytest.fixture
def sample_synthesis_result():
    """Sample audio synthesis result."""
    return SynthesisResult(
        audio_url='/tmp/audio/lesson_1.mp3',
        duration_seconds=600.0,
        chunks_synthesized=5,
        total_characters=500,
        synthesis_time_seconds=5.2
    )


@pytest.fixture
def session_manager():
    """Create a TutorSessionManager with mocked service components."""
    with patch.object(ContentExtractor, '__init__', return_value=None), \
         patch.object(ContentProcessor, '__init__', return_value=None), \
         patch.object(PodcastGenerator, '__init__', return_value=None), \
         patch.object(EnhancedAudioSynthesizer, '__init__', return_value=None), \
         patch.object(AudioCoordinator, '__init__', return_value=None):

        manager = TutorSessionManager()
        # Set default mock attributes
        manager.extractor = Mock(spec=ContentExtractor)
        manager.processor = Mock(spec=ContentProcessor)
        manager.generator = Mock(spec=PodcastGenerator)
        manager.synthesizer = Mock(spec=EnhancedAudioSynthesizer)
        manager.coordinator = Mock(spec=AudioCoordinator)

        return manager


# =============================================================================
# TutorSessionManager Tests
# =============================================================================

class TestTutorSessionManager:
    """Tests for TutorSessionManager class."""

    def test_initialization(self, session_manager):
        """Test manager initializes with empty sessions."""
        assert session_manager._sessions == {}
        assert session_manager.extractor is not None
        assert session_manager.processor is not None
        assert session_manager.generator is not None

    def test_create_session_success(
        self,
        session_manager,
        sample_raw_content,
        sample_processed_content,
        sample_lesson_topics
    ):
        """Test successful session creation from URL."""
        # Setup mocks
        session_manager.extractor.extract.return_value = sample_raw_content
        session_manager.processor.process.return_value = sample_processed_content
        session_manager.generator.check_health.return_value = True
        session_manager.generator.create_lesson_plan.return_value = sample_lesson_topics

        # Create session
        session = session_manager.create_session('https://example.com/python-basics')

        # Verify
        assert session is not None
        assert session.session_id in session_manager._sessions
        assert session.source_url == 'https://example.com/python-basics'
        assert session.status == SessionStatus.READY
        assert len(session.lessons) == 3

        # Verify lesson info
        assert session.lessons[0].title == 'Getting Started with Python'
        assert session.lessons[0].script_generated is False

    def test_create_session_extraction_failure(self, session_manager):
        """Test session creation handles extraction failure."""
        session_manager.extractor.extract.side_effect = ValueError("Failed to extract")

        session = session_manager.create_session('https://invalid-url.com')

        assert session.status == SessionStatus.ERROR
        assert session.error_message is not None

    def test_get_session_not_found(self, session_manager):
        """Test getting non-existent session returns None."""
        result = session_manager.get_session('non-existent-id')
        assert result is None

    def test_get_session_success(
        self,
        session_manager,
        sample_raw_content,
        sample_processed_content,
        sample_lesson_topics
    ):
        """Test getting existing session."""
        session_manager.extractor.extract.return_value = sample_raw_content
        session_manager.processor.process.return_value = sample_processed_content
        session_manager.generator.check_health.return_value = True
        session_manager.generator.create_lesson_plan.return_value = sample_lesson_topics

        session = session_manager.create_session('https://example.com/test')
        retrieved = session_manager.get_session(session.session_id)

        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    def test_delete_session(
        self,
        session_manager,
        sample_raw_content,
        sample_processed_content,
        sample_lesson_topics
    ):
        """Test deleting a session."""
        session_manager.extractor.extract.return_value = sample_raw_content
        session_manager.processor.process.return_value = sample_processed_content
        session_manager.generator.check_health.return_value = True
        session_manager.generator.create_lesson_plan.return_value = sample_lesson_topics

        session = session_manager.create_session('https://example.com/test')
        session_id = session.session_id

        result = session_manager.delete_session(session_id)
        assert result is True
        assert session_manager.get_session(session_id) is None

    def test_delete_session_not_found(self, session_manager):
        """Test deleting non-existent session."""
        result = session_manager.delete_session('non-existent-id')
        assert result is False

    def test_generate_lesson_session_not_found(self, session_manager):
        """Test generate_lesson with non-existent session."""
        with pytest.raises(ValueError, match="Session not found"):
            session_manager.generate_lesson('non-existent', 1)

    def test_list_sessions(
        self,
        session_manager,
        sample_raw_content,
        sample_processed_content,
        sample_lesson_topics
    ):
        """Test listing all sessions."""
        session_manager.extractor.extract.return_value = sample_raw_content
        session_manager.processor.process.return_value = sample_processed_content
        session_manager.generator.check_health.return_value = True
        session_manager.generator.create_lesson_plan.return_value = sample_lesson_topics

        # Create multiple sessions
        session1 = session_manager.create_session('https://example.com/test1')
        session2 = session_manager.create_session('https://example.com/test2')

        sessions = session_manager.list_sessions()

        assert len(sessions) == 2
        session_ids = [s.session_id for s in sessions]
        assert session1.session_id in session_ids
        assert session2.session_id in session_ids

    def test_check_health(self, session_manager):
        """Test health check returns component status."""
        session_manager.generator.check_health.return_value = True
        session_manager.synthesizer.check_health.return_value = {'polly': True}
        session_manager.coordinator.check_health.return_value = True

        health = session_manager.check_health()

        assert 'session_manager' in health
        assert 'active_sessions' in health
        assert 'extractor' in health
        assert 'generator' in health


# =============================================================================
# Session Data Tests
# =============================================================================

class TestSessionData:
    """Tests for session data structures."""

    def test_lesson_info_creation(self):
        """Test LessonInfo dataclass creation."""
        lesson = LessonInfo(
            lesson_number=1,
            title='Test Lesson',
            description='A test lesson'
        )

        assert lesson.lesson_number == 1
        assert lesson.title == 'Test Lesson'
        assert lesson.script_generated is False
        assert lesson.audio_generated is False
        assert lesson.script is None

    def test_lesson_info_to_dict(self):
        """Test LessonInfo serialization."""
        lesson = LessonInfo(
            lesson_number=1,
            title='Test Lesson',
            description='A test lesson',
            key_concepts=['concept1', 'concept2']
        )

        data = lesson.to_dict()

        assert data['lesson_number'] == 1
        assert data['title'] == 'Test Lesson'
        assert data['key_concepts'] == ['concept1', 'concept2']

    def test_tutor_session_data_creation(self):
        """Test TutorSessionData dataclass creation."""
        session = TutorSessionData(
            session_id='test-123',
            source_url='https://example.com/test'
        )

        assert session.session_id == 'test-123'
        assert session.source_url == 'https://example.com/test'
        assert session.status == SessionStatus.CREATED
        assert session.lessons == []
        assert session.error_message is None

    def test_tutor_session_data_to_dict(self):
        """Test TutorSessionData serialization."""
        session = TutorSessionData(
            session_id='test-123',
            source_url='https://example.com/test',
            status=SessionStatus.READY
        )

        data = session.to_dict()

        assert data['session_id'] == 'test-123'
        assert data['source_url'] == 'https://example.com/test'
        assert data['status'] == 'ready'

    def test_session_status_values(self):
        """Test SessionStatus enum values."""
        assert SessionStatus.CREATED.value == 'created'
        assert SessionStatus.VALIDATING.value == 'validating'
        assert SessionStatus.EXTRACTING.value == 'extracting'
        assert SessionStatus.PROCESSING.value == 'processing'
        assert SessionStatus.PLANNING.value == 'planning'
        assert SessionStatus.READY.value == 'ready'
        assert SessionStatus.GENERATING.value == 'generating'
        assert SessionStatus.COMPLETE.value == 'complete'
        assert SessionStatus.ERROR.value == 'error'


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_get_manager_singleton(self):
        """Test get_manager returns singleton instance."""
        # Reset global manager for clean test
        import services.tutor_session as ts
        ts._default_manager = None

        manager1 = get_manager()
        manager2 = get_manager()

        assert manager1 is manager2


# =============================================================================
# API v2 Route Tests (if Flask is available)
# =============================================================================

try:
    from flask import Flask
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False


@pytest.mark.skipif(not FLASK_AVAILABLE, reason="Flask not installed")
class TestAPIv2Routes:
    """Integration tests for API v2 endpoints."""

    @pytest.fixture
    def app(self):
        """Create test Flask app with API v2 routes."""
        from routes.api_v2 import register_v2_routes

        app = Flask(__name__)
        app.config['TESTING'] = True
        register_v2_routes(app)

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    @patch('routes.api_v2.get_manager')
    def test_health_endpoint(self, mock_get_manager, client):
        """Test GET /api/v2/health endpoint."""
        mock_manager = Mock()
        mock_manager.check_health.return_value = {
            'session_manager': True,
            'active_sessions': 0,
            'extractor': True,
            'processor': True,
            'generator': True,
            'synthesizer': {'polly': True},
            'coordinator': True
        }
        mock_get_manager.return_value = mock_manager

        response = client.get('/api/v2/health')

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'

    @patch('routes.api_v2.get_manager')
    def test_create_session_endpoint(self, mock_get_manager, client):
        """Test POST /api/v2/sessions endpoint."""
        mock_manager = Mock()
        mock_session = TutorSessionData(
            session_id='test-123',
            source_url='https://example.com/test',
            status=SessionStatus.READY
        )
        mock_session.lessons = [
            LessonInfo(1, 'Lesson 1', 'Description')
        ]
        mock_manager.create_session.return_value = mock_session
        mock_get_manager.return_value = mock_manager

        response = client.post(
            '/api/v2/sessions',
            json={'url': 'https://example.com/test'},
            content_type='application/json'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['session_id'] == 'test-123'

    @patch('routes.api_v2.get_manager')
    def test_create_session_missing_url(self, mock_get_manager, client):
        """Test POST /api/v2/sessions without URL."""
        response = client.post(
            '/api/v2/sessions',
            json={},
            content_type='application/json'
        )

        assert response.status_code == 400

    @patch('routes.api_v2.get_manager')
    def test_get_session_endpoint(self, mock_get_manager, client):
        """Test GET /api/v2/sessions/<id> endpoint."""
        mock_manager = Mock()
        mock_session = TutorSessionData(
            session_id='test-123',
            source_url='https://example.com/test',
            status=SessionStatus.READY
        )
        mock_session.lessons = []
        mock_manager.get_session.return_value = mock_session
        mock_get_manager.return_value = mock_manager

        response = client.get('/api/v2/sessions/test-123')

        assert response.status_code == 200
        data = response.get_json()
        assert data['session_id'] == 'test-123'

    @patch('routes.api_v2.get_manager')
    def test_get_session_not_found(self, mock_get_manager, client):
        """Test GET /api/v2/sessions/<id> for non-existent session."""
        mock_manager = Mock()
        mock_manager.get_session.return_value = None
        mock_get_manager.return_value = mock_manager

        response = client.get('/api/v2/sessions/non-existent')

        assert response.status_code == 404

    @patch('routes.api_v2.get_manager')
    def test_list_sessions_endpoint(self, mock_get_manager, client):
        """Test GET /api/v2/sessions endpoint."""
        mock_manager = Mock()
        mock_session = TutorSessionData(
            session_id='test-123',
            source_url='https://example.com/test',
            status=SessionStatus.READY
        )
        mock_session.lessons = []
        mock_manager.list_sessions.return_value = [mock_session]
        mock_get_manager.return_value = mock_manager

        response = client.get('/api/v2/sessions')

        assert response.status_code == 200
        data = response.get_json()
        assert 'sessions' in data
        assert len(data['sessions']) == 1

    @patch('routes.api_v2.get_manager')
    def test_delete_session_endpoint(self, mock_get_manager, client):
        """Test DELETE /api/v2/sessions/<id> endpoint."""
        mock_manager = Mock()
        mock_manager.delete_session.return_value = True
        mock_get_manager.return_value = mock_manager

        response = client.delete('/api/v2/sessions/test-123')

        assert response.status_code == 204  # DELETE returns 204 No Content on success


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
