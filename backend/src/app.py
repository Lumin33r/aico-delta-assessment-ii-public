"""
AI Personal Tutor - Flask Backend API

This application provides endpoints for:
- Ingesting URL content for lesson generation
- Creating podcast-style lessons with two AI hosts
- Generating multi-voice audio via AWS Polly
- Managing lesson sessions

Hosts:
- Alex (Matthew voice): Senior engineer, explains concepts clearly
- Sam (Joanna voice): Curious learner, asks clarifying questions
"""

import os
import json
import uuid
import logging
from datetime import datetime
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

# Import services
from services.content_extractor import ContentExtractor
from services.content_processor import ContentProcessor
from services.podcast_generator import PodcastGenerator
from services.audio_synthesizer import AudioSynthesizer

# Import utilities
from utils.url_validator import URLValidator, ContentType
from utils.cache import ContentCache, get_cache

# Import API v2 routes
from routes.api_v2 import register_v2_routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=os.getenv('CORS_ORIGINS', '*').split(','))

# Configuration
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2')
AWS_REGION = os.getenv('AWS_REGION', 'us-west-2')
S3_BUCKET = os.getenv('S3_BUCKET', 'ai-tutor-audio')
LESSONS_PER_URL = int(os.getenv('LESSONS_PER_URL', '3'))

# Initialize services
content_extractor = ContentExtractor()
content_processor = ContentProcessor(chunk_size=1500, chunk_overlap=200)
url_validator = URLValidator(timeout=15)
content_cache = get_cache(max_entries=100, default_ttl_seconds=3600)
podcast_generator = PodcastGenerator(
    ollama_host=OLLAMA_HOST,
    model=OLLAMA_MODEL
)
audio_synthesizer = AudioSynthesizer(
    region=AWS_REGION,
    bucket=S3_BUCKET
)

# In-memory session storage (Redis-ready pattern)
sessions = {}

# Register API v2 routes
register_v2_routes(app)


class TutorSession:
    """Represents a tutoring session for a user."""

    def __init__(self, session_id: str, source_url: str):
        self.session_id = session_id
        self.source_url = source_url
        self.created_at = datetime.utcnow().isoformat()
        self.content = None
        self.processed_content = None  # ProcessedContent from content_processor
        self.topics = []
        self.lessons = []
        self.status = 'pending'  # pending, extracting, processing, planning, ready, error
        self.error_message = None

    def to_dict(self):
        return {
            'session_id': self.session_id,
            'source_url': self.source_url,
            'created_at': self.created_at,
            'status': self.status,
            'topics': self.topics,
            'content_summary': {
                'title': self.processed_content.title if self.processed_content else None,
                'word_count': self.processed_content.total_words if self.processed_content else 0,
                'reading_time_minutes': self.processed_content.reading_time_minutes if self.processed_content else 0,
                'extracted_topics': self.processed_content.topics if self.processed_content else [],
                'key_concepts': self.processed_content.key_concepts[:5] if self.processed_content else []
            } if self.processed_content else None,
            'lessons': [
                {
                    'lesson_number': i + 1,
                    'title': lesson.get('title', f'Lesson {i + 1}'),
                    'topic': lesson.get('topic', ''),
                    'has_audio': lesson.get('audio_url') is not None,
                    'duration_seconds': lesson.get('duration_seconds', 0)
                }
                for i, lesson in enumerate(self.lessons)
            ],
            'error_message': self.error_message
        }


# =============================================================================
# Health & Info Endpoints
# =============================================================================

@app.route('/', methods=['GET'])
def index():
    """API documentation and available endpoints."""
    return jsonify({
        'service': 'AI Personal Tutor API',
        'version': '1.0.0',
        'description': 'Podcast-style learning from any URL',
        'hosts': {
            'alex': {
                'role': 'Senior Engineer',
                'voice': 'Matthew (Neural)',
                'personality': 'Patient expert who explains concepts clearly'
            },
            'sam': {
                'role': 'Curious Learner',
                'voice': 'Joanna (Neural)',
                'personality': 'Asks great questions, summarizes key points'
            }
        },
        'endpoints': [
            {
                'path': '/health',
                'method': 'GET',
                'description': 'Health check endpoint'
            },
            {
                'path': '/api/ingest',
                'method': 'POST',
                'description': 'Ingest URL content and create lesson plan',
                'request_body': {
                    'url': 'string - URL to extract content from',
                    'num_lessons': 'int (optional) - Number of lessons to generate (default: 3)'
                },
                'response': {
                    'session_id': 'string - Session identifier for future requests',
                    'status': 'string - Processing status',
                    'topics': 'array - Extracted topics for lessons'
                }
            },
            {
                'path': '/api/session/<session_id>',
                'method': 'GET',
                'description': 'Get session status and lesson list'
            },
            {
                'path': '/api/lesson/<session_id>/<lesson_num>',
                'method': 'GET',
                'description': 'Get lesson details and transcript'
            },
            {
                'path': '/api/lesson/<session_id>/<lesson_num>/audio',
                'method': 'GET',
                'description': 'Get audio URL for a lesson'
            },
            {
                'path': '/api/lesson/<session_id>/<lesson_num>/generate',
                'method': 'POST',
                'description': 'Generate podcast audio for a specific lesson'
            }
        ]
    }), 200


@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for load balancers."""
    # Check service dependencies
    services_status = {
        'ollama': podcast_generator.check_health(),
        'polly': audio_synthesizer.check_health()
    }

    all_healthy = all(services_status.values())

    return jsonify({
        'status': 'healthy' if all_healthy else 'degraded',
        'timestamp': datetime.utcnow().isoformat(),
        'services': services_status
    }), 200 if all_healthy else 503


# =============================================================================
# Content Ingestion Endpoints
# =============================================================================

@app.route('/api/ingest', methods=['POST'])
def ingest_url():
    """
    Ingest URL content and create a lesson plan.

    This endpoint:
    1. Extracts content from the provided URL
    2. Analyzes content to identify key topics
    3. Creates a session with planned lessons
    4. Returns session ID for tracking
    """
    try:
        data = request.get_json()

        if not data or 'url' not in data:
            return jsonify({
                'error': 'Missing required field: url',
                'example': {'url': 'https://example.com/article'}
            }), 400

        url = data['url']
        num_lessons = data.get('num_lessons', LESSONS_PER_URL)
        use_cache = data.get('use_cache', True)

        # Validate URL format and accessibility
        validation = url_validator.validate(url)
        if not validation.is_valid:
            return jsonify({
                'error': 'URL validation failed',
                'detail': validation.error,
                'url': url
            }), 400

        # Use final URL after redirects
        url = validation.final_url

        # Check if content type is supported
        if validation.content_type not in [ContentType.HTML, ContentType.TEXT, ContentType.MARKDOWN]:
            return jsonify({
                'error': 'Unsupported content type',
                'detail': f'Content type {validation.content_type.value} is not supported',
                'supported': ['html', 'text', 'markdown']
            }), 400

        # Create session
        session_id = str(uuid.uuid4())
        session = TutorSession(session_id, url)
        sessions[session_id] = session

        logger.info(f"Created session {session_id} for URL: {url}")

        # Check cache first
        cached_content = None
        if use_cache:
            cached_content = content_cache.get(url)
            if cached_content:
                logger.info(f"Cache hit for URL: {url}")

        # Extract content from URL (or use cache)
        try:
            session.status = 'extracting'

            if cached_content:
                content = cached_content
            else:
                content = content_extractor.extract(url)
                # Cache the extracted content
                content_cache.set(url, content)

            session.content = content
            logger.info(f"Extracted {len(content.get('text', ''))} chars from {url}")

            # Process content for better LLM consumption
            session.status = 'processing'
            processed = content_processor.process(content)
            session.processed_content = processed
            logger.info(f"Processed into {len(processed.chunks)} chunks, {len(processed.topics)} topics")

        except Exception as e:
            session.status = 'error'
            session.error_message = f"Failed to extract content: {str(e)}"
            logger.error(f"Content extraction failed: {e}")
            return jsonify(session.to_dict()), 422

        # Generate lesson plan (topics)
        try:
            session.status = 'planning'
            topics = podcast_generator.create_lesson_plan(
                content=content['text'],
                title=content.get('title', 'Untitled'),
                num_lessons=num_lessons
            )
            session.topics = topics

            # Initialize lesson placeholders
            session.lessons = [
                {
                    'topic': topic,
                    'title': topic.get('title', f'Lesson {i + 1}'),
                    'script': None,
                    'audio_url': None,
                    'duration_seconds': 0
                }
                for i, topic in enumerate(topics)
            ]

            session.status = 'ready'
            logger.info(f"Created {len(topics)} lesson topics for session {session_id}")

        except Exception as e:
            session.status = 'error'
            session.error_message = f"Failed to create lesson plan: {str(e)}"
            logger.error(f"Lesson planning failed: {e}")
            return jsonify(session.to_dict()), 500

        return jsonify(session.to_dict()), 201

    except Exception as e:
        logger.error(f"Unexpected error in ingest: {e}")
        return jsonify({
            'error': 'Internal server error',
            'detail': str(e)
        }), 500


# =============================================================================
# Session Management Endpoints
# =============================================================================

@app.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get session status and lesson list."""
    session = sessions.get(session_id)

    if not session:
        return jsonify({
            'error': 'Session not found',
            'session_id': session_id
        }), 404

    return jsonify(session.to_dict()), 200


@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    """List all active sessions."""
    return jsonify({
        'sessions': [s.to_dict() for s in sessions.values()],
        'count': len(sessions)
    }), 200


# =============================================================================
# Lesson Endpoints
# =============================================================================

@app.route('/api/lesson/<session_id>/<int:lesson_num>', methods=['GET'])
def get_lesson(session_id, lesson_num):
    """Get lesson details including transcript."""
    session = sessions.get(session_id)

    if not session:
        return jsonify({'error': 'Session not found'}), 404

    if lesson_num < 1 or lesson_num > len(session.lessons):
        return jsonify({
            'error': 'Invalid lesson number',
            'available_lessons': len(session.lessons)
        }), 404

    lesson = session.lessons[lesson_num - 1]

    return jsonify({
        'session_id': session_id,
        'lesson_number': lesson_num,
        'title': lesson.get('title', f'Lesson {lesson_num}'),
        'topic': lesson.get('topic', {}),
        'script': lesson.get('script'),
        'audio_url': lesson.get('audio_url'),
        'duration_seconds': lesson.get('duration_seconds', 0),
        'has_audio': lesson.get('audio_url') is not None
    }), 200


@app.route('/api/lesson/<session_id>/<int:lesson_num>/generate', methods=['POST'])
def generate_lesson_audio(session_id, lesson_num):
    """
    Generate podcast-style audio for a specific lesson.

    This endpoint:
    1. Generates a two-host dialogue script using Ollama
    2. Synthesizes multi-voice audio using AWS Polly
    3. Uploads to S3 and returns the audio URL
    """
    session = sessions.get(session_id)

    if not session:
        return jsonify({'error': 'Session not found'}), 404

    if session.status != 'ready':
        return jsonify({
            'error': 'Session not ready',
            'status': session.status
        }), 400

    if lesson_num < 1 or lesson_num > len(session.lessons):
        return jsonify({
            'error': 'Invalid lesson number',
            'available_lessons': len(session.lessons)
        }), 404

    lesson_idx = lesson_num - 1
    lesson = session.lessons[lesson_idx]

    # Check if already generated
    if lesson.get('audio_url'):
        return jsonify({
            'message': 'Audio already generated',
            'audio_url': lesson['audio_url'],
            'duration_seconds': lesson.get('duration_seconds', 0)
        }), 200

    try:
        # Generate dialogue script
        logger.info(f"Generating script for session {session_id}, lesson {lesson_num}")
        script = podcast_generator.generate_episode_script(
            topic=lesson['topic'],
            content=session.content['text'],
            lesson_number=lesson_num,
            total_lessons=len(session.lessons)
        )

        lesson['script'] = script
        logger.info(f"Script generated: {len(script)} dialogue segments")

        # Synthesize audio
        logger.info(f"Synthesizing audio for session {session_id}, lesson {lesson_num}")
        audio_result = audio_synthesizer.synthesize_podcast(
            script=script,
            session_id=session_id,
            lesson_num=lesson_num
        )

        lesson['audio_url'] = audio_result['url']
        lesson['duration_seconds'] = audio_result['duration_seconds']

        logger.info(f"Audio generated: {audio_result['duration_seconds']}s")

        return jsonify({
            'message': 'Audio generated successfully',
            'audio_url': audio_result['url'],
            'duration_seconds': audio_result['duration_seconds'],
            'transcript': script
        }), 201

    except Exception as e:
        logger.error(f"Audio generation failed: {e}")
        return jsonify({
            'error': 'Failed to generate audio',
            'detail': str(e)
        }), 500


@app.route('/api/lesson/<session_id>/<int:lesson_num>/audio', methods=['GET'])
def get_lesson_audio(session_id, lesson_num):
    """Get audio URL for a lesson (redirects to S3 presigned URL)."""
    session = sessions.get(session_id)

    if not session:
        return jsonify({'error': 'Session not found'}), 404

    if lesson_num < 1 or lesson_num > len(session.lessons):
        return jsonify({'error': 'Invalid lesson number'}), 404

    lesson = session.lessons[lesson_num - 1]

    if not lesson.get('audio_url'):
        return jsonify({
            'error': 'Audio not generated yet',
            'hint': f'POST /api/lesson/{session_id}/{lesson_num}/generate to create audio'
        }), 404

    # Return fresh presigned URL
    fresh_url = audio_synthesizer.get_presigned_url(
        session_id=session_id,
        lesson_num=lesson_num
    )

    return jsonify({
        'audio_url': fresh_url,
        'duration_seconds': lesson.get('duration_seconds', 0)
    }), 200


# =============================================================================
# Lex Integration Endpoints (for Lambda fulfillment)
# =============================================================================

@app.route('/api/lex/create-lesson', methods=['POST'])
def lex_create_lesson():
    """
    Endpoint called by Lex fulfillment Lambda.
    Creates a new lesson from the provided URL.
    """
    try:
        data = request.get_json()
        url = data.get('url')
        user_id = data.get('user_id', 'anonymous')

        if not url:
            return jsonify({
                'success': False,
                'message': "I need a URL to create your lesson. Could you provide one?"
            }), 400

        # Call the ingest endpoint internally
        session_id = str(uuid.uuid4())
        session = TutorSession(session_id, url)
        sessions[session_id] = session

        # Quick content extraction
        content = content_extractor.extract(url)
        session.content = content

        # Generate topics
        topics = podcast_generator.create_lesson_plan(
            content=content['text'],
            title=content.get('title', 'Untitled'),
            num_lessons=3
        )
        session.topics = topics
        session.lessons = [
            {'topic': t, 'title': t.get('title', f'Lesson {i+1}')}
            for i, t in enumerate(topics)
        ]
        session.status = 'ready'

        # Format response for Lex
        lesson_titles = [l['title'] for l in session.lessons]

        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': f"Great! I've analyzed the content and created {len(topics)} lessons for you: " +
                      ", ".join(lesson_titles) +
                      ". Would you like to start with lesson 1?",
            'lessons': lesson_titles
        }), 200

    except Exception as e:
        logger.error(f"Lex create-lesson failed: {e}")
        return jsonify({
            'success': False,
            'message': f"I had trouble processing that URL. Error: {str(e)}"
        }), 500


@app.route('/api/lex/create-lesson-async', methods=['POST'])
def lex_create_lesson_async():
    """
    Async version of create-lesson endpoint.
    Starts lesson creation in background and returns immediately.
    Use /api/lex/session-status to check when lessons are ready.
    """
    import threading

    try:
        data = request.get_json()
        url = data.get('url')
        user_id = data.get('user_id', 'anonymous')

        if not url:
            return jsonify({
                'success': False,
                'message': "I need a URL to create your lesson. Could you provide one?"
            }), 400

        # Create session immediately
        session_id = str(uuid.uuid4())
        session = TutorSession(session_id, url)
        session.status = 'processing'
        sessions[session_id] = session

        # Store user_id -> session_id mapping for easy lookup
        if not hasattr(app, 'user_sessions'):
            app.user_sessions = {}
        app.user_sessions[user_id] = session_id

        def process_lessons():
            """Background task to create lessons."""
            try:
                logger.info(f"[Async] Starting lesson creation for session {session_id}")
                session.status = 'extracting'

                # Extract content
                content = content_extractor.extract(url)
                session.content = content
                session.status = 'planning'

                # Generate topics
                topics = podcast_generator.create_lesson_plan(
                    content=content['text'],
                    title=content.get('title', 'Untitled'),
                    num_lessons=3
                )
                session.topics = topics
                session.lessons = [
                    {'topic': t, 'title': t.get('title', f'Lesson {i+1}')}
                    for i, t in enumerate(topics)
                ]
                session.status = 'ready'
                logger.info(f"[Async] Lesson creation complete for session {session_id}")

            except Exception as e:
                logger.error(f"[Async] Lesson creation failed for session {session_id}: {e}")
                session.status = 'error'
                session.error_message = str(e)

        # Start background thread
        thread = threading.Thread(target=process_lessons, daemon=True)
        thread.start()

        return jsonify({
            'success': True,
            'session_id': session_id,
            'status': 'processing',
            'message': "I'm analyzing that content now. This usually takes about a minute. Say 'check status' or 'are my lessons ready?' to see when they're done!"
        }), 202  # 202 Accepted

    except Exception as e:
        logger.error(f"Lex create-lesson-async failed: {e}")
        return jsonify({
            'success': False,
            'message': f"I had trouble starting the lesson creation. Error: {str(e)}"
        }), 500


@app.route('/api/lex/session-status', methods=['POST'])
def lex_session_status():
    """
    Check the status of a lesson creation session.
    Can lookup by session_id or user_id.
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        user_id = data.get('user_id')

        # Try to find session by user_id if no session_id provided
        if not session_id and user_id:
            if hasattr(app, 'user_sessions'):
                session_id = app.user_sessions.get(user_id)

        if not session_id:
            return jsonify({
                'success': False,
                'status': 'not_found',
                'message': "I don't have any lessons in progress for you. Share a URL to get started!"
            }), 404

        session = sessions.get(session_id)
        if not session:
            return jsonify({
                'success': False,
                'status': 'not_found',
                'message': "I couldn't find that session. It may have expired. Share a new URL to create lessons!"
            }), 404

        if session.status == 'ready':
            lesson_titles = [l['title'] for l in session.lessons]
            return jsonify({
                'success': True,
                'status': 'ready',
                'session_id': session_id,
                'message': f"Your lessons are ready! I created {len(lesson_titles)} lessons: " +
                          ", ".join(lesson_titles) +
                          ". Would you like to start with lesson 1?",
                'lessons': lesson_titles
            }), 200
        elif session.status == 'error':
            return jsonify({
                'success': False,
                'status': 'error',
                'message': f"I had trouble creating lessons from that URL: {session.error_message}. Please try a different URL."
            }), 200
        else:
            status_messages = {
                'processing': "I'm still working on your lessons...",
                'extracting': "I'm reading and extracting content from that page...",
                'planning': "I'm creating your lesson plan now..."
            }
            return jsonify({
                'success': True,
                'status': session.status,
                'session_id': session_id,
                'message': status_messages.get(session.status, "Still processing...") + " Check back in a moment!"
            }), 200

    except Exception as e:
        logger.error(f"Lex session-status failed: {e}")
        return jsonify({
            'success': False,
            'message': f"I had trouble checking the status. Error: {str(e)}"
        }), 500


@app.route('/api/lex/start-lesson', methods=['POST'])
def lex_start_lesson():
    """
    Endpoint called by Lex when user wants to start a lesson.
    Triggers audio generation if needed.
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        lesson_num = data.get('lesson_number', 1)

        if not session_id:
            return jsonify({
                'success': False,
                'message': "I don't have an active session. Please provide a URL first."
            }), 400

        session = sessions.get(session_id)
        if not session:
            return jsonify({
                'success': False,
                'message': "I couldn't find that session. Let's start fresh - what URL would you like to learn from?"
            }), 404

        lesson = session.lessons[lesson_num - 1]

        # Check if audio exists
        if lesson.get('audio_url'):
            return jsonify({
                'success': True,
                'message': f"Your lesson is ready! Click play to listen to Alex and Sam discuss: {lesson['title']}",
                'audio_url': lesson['audio_url'],
                'has_audio': True
            }), 200

        # Generate audio (this might take a while)
        return jsonify({
            'success': True,
            'message': f"I'm preparing your lesson on '{lesson['title']}'. Alex and Sam are getting ready to record. This will take about 30 seconds...",
            'session_id': session_id,
            'lesson_number': lesson_num,
            'needs_generation': True
        }), 202

    except Exception as e:
        logger.error(f"Lex start-lesson failed: {e}")
        return jsonify({
            'success': False,
            'message': f"Something went wrong: {str(e)}"
        }), 500


@app.route('/api/lex/progress', methods=['POST'])
def lex_progress():
    """
    Get learning progress for a session.
    Called by Lex when user asks about their progress.
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({
                'success': False,
                'message': "You haven't started any lessons yet. Share a URL to get started!"
            }), 400

        session = sessions.get(session_id)
        if not session:
            return jsonify({
                'success': False,
                'message': "I couldn't find that session. Share a new URL to create lessons!"
            }), 404

        if session.status != 'ready':
            return jsonify({
                'success': True,
                'message': f"Your lessons are still being prepared (status: {session.status}). Check back in a moment!"
            }), 200

        # Count completed lessons (those with audio generated)
        total_lessons = len(session.lessons)
        completed_lessons = sum(1 for l in session.lessons if l.get('audio_url'))

        lesson_titles = [l['title'] for l in session.lessons]

        if completed_lessons == 0:
            message = f"You have {total_lessons} lessons ready: {', '.join(lesson_titles)}. Say 'start lesson 1' to begin!"
        elif completed_lessons < total_lessons:
            message = f"You've listened to {completed_lessons} of {total_lessons} lessons. Ready for lesson {completed_lessons + 1}?"
        else:
            message = f"Congratulations! You've completed all {total_lessons} lessons. Want to review any of them?"

        return jsonify({
            'success': True,
            'message': message,
            'total_lessons': total_lessons,
            'completed_lessons': completed_lessons,
            'lessons': lesson_titles
        }), 200

    except Exception as e:
        logger.error(f"Lex progress failed: {e}")
        return jsonify({
            'success': False,
            'message': f"I couldn't get your progress: {str(e)}"
        }), 500


@app.route('/api/lex/next-lesson', methods=['POST'])
def lex_next_lesson():
    """
    Get the next lesson in the sequence.
    Called by Lex when user wants to continue.
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        current_lesson = data.get('current_lesson', 0)

        if not session_id:
            return jsonify({
                'success': False,
                'message': "You haven't started any lessons yet. Share a URL to get started!"
            }), 400

        session = sessions.get(session_id)
        if not session:
            return jsonify({
                'success': False,
                'message': "I couldn't find that session. Share a new URL to create lessons!"
            }), 404

        if session.status != 'ready':
            return jsonify({
                'success': False,
                'message': f"Your lessons are still being prepared. Check back in a moment!"
            }), 200

        next_lesson_num = current_lesson + 1
        if next_lesson_num > len(session.lessons):
            return jsonify({
                'success': True,
                'message': "You've completed all the lessons! Great job! Would you like to review any of them?",
                'completed': True
            }), 200

        lesson = session.lessons[next_lesson_num - 1]
        return jsonify({
            'success': True,
            'message': f"Up next: Lesson {next_lesson_num} - {lesson['title']}. Say 'start lesson {next_lesson_num}' when you're ready!",
            'next_lesson': next_lesson_num,
            'title': lesson['title'],
            'has_audio': bool(lesson.get('audio_url'))
        }), 200

    except Exception as e:
        logger.error(f"Lex next-lesson failed: {e}")
        return jsonify({
            'success': False,
            'message': f"Something went wrong: {str(e)}"
        }), 500


@app.route('/api/lex/repeat-lesson', methods=['POST'])
def lex_repeat_lesson():
    """
    Repeat the current or specified lesson.
    Called by Lex when user wants to hear a lesson again.
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        lesson_num = data.get('lesson_number', 1)

        if not session_id:
            return jsonify({
                'success': False,
                'message': "You haven't started any lessons yet. Share a URL to get started!"
            }), 400

        session = sessions.get(session_id)
        if not session:
            return jsonify({
                'success': False,
                'message': "I couldn't find that session. Share a new URL to create lessons!"
            }), 404

        if session.status != 'ready':
            return jsonify({
                'success': False,
                'message': f"Your lessons are still being prepared. Check back in a moment!"
            }), 200

        if lesson_num < 1 or lesson_num > len(session.lessons):
            return jsonify({
                'success': False,
                'message': f"I only have {len(session.lessons)} lessons. Which one would you like to repeat?"
            }), 400

        lesson = session.lessons[lesson_num - 1]

        if lesson.get('audio_url'):
            return jsonify({
                'success': True,
                'message': f"Playing lesson {lesson_num} - {lesson['title']} again!",
                'audio_url': lesson['audio_url'],
                'has_audio': True
            }), 200
        else:
            return jsonify({
                'success': True,
                'message': f"Let me prepare lesson {lesson_num} - {lesson['title']} for you. One moment...",
                'needs_generation': True,
                'lesson_number': lesson_num
            }), 202

    except Exception as e:
        logger.error(f"Lex repeat-lesson failed: {e}")
        return jsonify({
            'success': False,
            'message': f"Something went wrong: {str(e)}"
        }), 500


# =============================================================================
# Admin & Stats Endpoints
# =============================================================================

@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """Get content cache statistics."""
    stats = content_cache.get_stats()
    return jsonify({
        'hits': stats.hits,
        'misses': stats.misses,
        'hit_rate': round(stats.hit_rate, 2),
        'evictions': stats.evictions,
        'current_size_bytes': stats.current_size,
        'max_size_bytes': stats.max_size,
        'entry_count': stats.entry_count
    }), 200


@app.route('/api/cache/clear', methods=['POST'])
def cache_clear():
    """Clear the content cache."""
    cleared = content_cache.clear()
    return jsonify({
        'cleared': cleared,
        'message': f'Cleared {cleared} cache entries'
    }), 200


@app.route('/api/validate', methods=['POST'])
def validate_url():
    """
    Validate a URL without ingesting it.

    Useful for checking if a URL is accessible before starting a session.
    """
    data = request.get_json()

    if not data or 'url' not in data:
        return jsonify({'error': 'Missing required field: url'}), 400

    url = data['url']
    result = url_validator.validate(url)

    return jsonify({
        'is_valid': result.is_valid,
        'url': result.url,
        'final_url': result.final_url,
        'content_type': result.content_type.value,
        'content_length': result.content_length,
        'status_code': result.status_code,
        'redirect_count': len(result.redirect_chain),
        'response_time_ms': result.response_time_ms,
        'error': result.error,
        'cached': url in content_cache
    }), 200 if result.is_valid else 400


# =============================================================================
# Error Handlers
# =============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    logger.info(f"Starting AI Personal Tutor API on port {port}")
    logger.info(f"Ollama host: {OLLAMA_HOST}")
    logger.info(f"AWS Region: {AWS_REGION}")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
