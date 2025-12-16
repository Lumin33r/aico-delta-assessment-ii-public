"""
API Routes (v2)

Enhanced REST API endpoints using the TutorSessionManager.

Endpoints:
- POST /api/v2/sessions - Create session from URL
- GET  /api/v2/sessions - List all sessions
- GET  /api/v2/sessions/<id> - Get session details
- DELETE /api/v2/sessions/<id> - Delete session

- GET  /api/v2/sessions/<id>/lessons - List lessons
- GET  /api/v2/sessions/<id>/lessons/<num> - Get lesson details
- POST /api/v2/sessions/<id>/lessons/<num>/generate - Generate lesson
- GET  /api/v2/sessions/<id>/lessons/<num>/transcript - Get transcript
- GET  /api/v2/sessions/<id>/lessons/<num>/audio - Get audio URL

- GET  /api/v2/health - Health check
"""

import logging
from flask import Blueprint, jsonify, request, Response
from functools import wraps

from services.tutor_session import (
    TutorSessionManager, TutorSessionData, LessonInfo, SessionStatus,
    get_manager
)

logger = logging.getLogger(__name__)

# Create Blueprint
api_v2 = Blueprint('api_v2', __name__, url_prefix='/api/v2')


# =============================================================================
# Error Handling
# =============================================================================

def handle_errors(f):
    """Decorator for consistent error handling."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            return jsonify({
                'error': 'Validation Error',
                'message': str(e)
            }), 400
        except KeyError as e:
            return jsonify({
                'error': 'Not Found',
                'message': f'Resource not found: {e}'
            }), 404
        except Exception as e:
            logger.error(f"API error in {f.__name__}: {e}")
            return jsonify({
                'error': 'Internal Server Error',
                'message': str(e)
            }), 500
    return wrapper


# =============================================================================
# Health Endpoint
# =============================================================================

@api_v2.route('/health', methods=['GET'])
@handle_errors
def health_check():
    """
    Health check endpoint.

    Returns status of all components.
    """
    manager = get_manager()
    health = manager.check_health()

    all_healthy = all(
        v if isinstance(v, bool) else v.get('polly', False)
        for k, v in health.items()
        if k not in ['active_sessions']
    )

    return jsonify({
        'status': 'healthy' if all_healthy else 'degraded',
        'components': health
    }), 200 if all_healthy else 503


# =============================================================================
# Session Endpoints
# =============================================================================

@api_v2.route('/sessions', methods=['POST'])
@handle_errors
def create_session():
    """
    Create a new tutoring session.

    Request Body:
        url: string - URL to extract content from
        num_lessons: int (optional) - Number of lessons (default: 3)
        user_id: string (optional) - User identifier
        metadata: object (optional) - Additional metadata

    Returns:
        201: Session created successfully
        400: Invalid request
        422: Content extraction failed
    """
    data = request.get_json()

    if not data or 'url' not in data:
        return jsonify({
            'error': 'Missing required field',
            'message': 'url is required',
            'example': {'url': 'https://example.com/article', 'num_lessons': 3}
        }), 400

    url = data['url']
    num_lessons = data.get('num_lessons', 3)
    user_id = data.get('user_id')
    metadata = data.get('metadata', {})

    # Validate num_lessons
    if not isinstance(num_lessons, int) or num_lessons < 1 or num_lessons > 10:
        return jsonify({
            'error': 'Invalid num_lessons',
            'message': 'num_lessons must be between 1 and 10'
        }), 400

    manager = get_manager()
    session = manager.create_session(
        url=url,
        num_lessons=num_lessons,
        user_id=user_id,
        metadata=metadata
    )

    if session.status == SessionStatus.ERROR:
        return jsonify({
            'error': 'Session creation failed',
            'message': session.error_message,
            'session': session.to_dict()
        }), 422

    return jsonify(session.to_dict()), 201


@api_v2.route('/sessions', methods=['GET'])
@handle_errors
def list_sessions():
    """
    List all sessions.

    Query Parameters:
        user_id: string (optional) - Filter by user
        status: string (optional) - Filter by status
        limit: int (optional) - Max results (default: 50)

    Returns:
        200: List of sessions
    """
    user_id = request.args.get('user_id')
    status_str = request.args.get('status')
    limit = int(request.args.get('limit', 50))

    status = None
    if status_str:
        try:
            status = SessionStatus(status_str)
        except ValueError:
            return jsonify({
                'error': 'Invalid status',
                'valid_values': [s.value for s in SessionStatus]
            }), 400

    manager = get_manager()
    sessions = manager.list_sessions(user_id=user_id, status=status)

    # Apply limit
    sessions = sessions[:limit]

    return jsonify({
        'sessions': [s.to_dict() for s in sessions],
        'count': len(sessions)
    }), 200


@api_v2.route('/sessions/<session_id>', methods=['GET'])
@handle_errors
def get_session(session_id):
    """
    Get session details.

    Path Parameters:
        session_id: Session identifier

    Returns:
        200: Session details
        404: Session not found
    """
    manager = get_manager()
    session = manager.get_session(session_id)

    if not session:
        return jsonify({
            'error': 'Session not found',
            'session_id': session_id
        }), 404

    return jsonify(session.to_dict()), 200


@api_v2.route('/sessions/<session_id>', methods=['DELETE'])
@handle_errors
def delete_session(session_id):
    """
    Delete a session.

    Path Parameters:
        session_id: Session identifier

    Returns:
        204: Session deleted
        404: Session not found
    """
    manager = get_manager()

    if not manager.delete_session(session_id):
        return jsonify({
            'error': 'Session not found',
            'session_id': session_id
        }), 404

    return '', 204


# =============================================================================
# Lesson Endpoints
# =============================================================================

@api_v2.route('/sessions/<session_id>/lessons', methods=['GET'])
@handle_errors
def list_lessons(session_id):
    """
    List all lessons in a session.

    Path Parameters:
        session_id: Session identifier

    Returns:
        200: List of lessons
        404: Session not found
    """
    manager = get_manager()
    session = manager.get_session(session_id)

    if not session:
        return jsonify({
            'error': 'Session not found',
            'session_id': session_id
        }), 404

    return jsonify({
        'session_id': session_id,
        'lessons': [l.to_dict() for l in session.lessons],
        'total': len(session.lessons)
    }), 200


@api_v2.route('/sessions/<session_id>/lessons/<int:lesson_num>', methods=['GET'])
@handle_errors
def get_lesson(session_id, lesson_num):
    """
    Get lesson details.

    Path Parameters:
        session_id: Session identifier
        lesson_num: Lesson number (1-indexed)

    Returns:
        200: Lesson details
        404: Session or lesson not found
    """
    manager = get_manager()
    lesson = manager.get_lesson(session_id, lesson_num)

    if not lesson:
        return jsonify({
            'error': 'Lesson not found',
            'session_id': session_id,
            'lesson_num': lesson_num
        }), 404

    return jsonify(lesson.to_dict()), 200


@api_v2.route('/sessions/<session_id>/lessons/<int:lesson_num>/generate', methods=['POST'])
@handle_errors
def generate_lesson(session_id, lesson_num):
    """
    Generate script and audio for a lesson.

    Path Parameters:
        session_id: Session identifier
        lesson_num: Lesson number (1-indexed)

    Request Body:
        generate_audio: bool (optional) - Generate audio (default: true)
        target_duration: int (optional) - Target duration in minutes (default: 10)

    Returns:
        201: Lesson generated
        200: Lesson already generated
        400: Session not ready
        404: Session or lesson not found
    """
    data = request.get_json() or {}
    generate_audio = data.get('generate_audio', True)
    target_duration = data.get('target_duration', 10)

    manager = get_manager()
    session = manager.get_session(session_id)

    if not session:
        return jsonify({
            'error': 'Session not found',
            'session_id': session_id
        }), 404

    if session.status not in [SessionStatus.READY, SessionStatus.GENERATING, SessionStatus.COMPLETE]:
        return jsonify({
            'error': 'Session not ready',
            'status': session.status.value,
            'message': 'Wait for session to be ready before generating lessons'
        }), 400

    # Check if already generated
    lesson = manager.get_lesson(session_id, lesson_num)
    if not lesson:
        return jsonify({
            'error': 'Lesson not found',
            'lesson_num': lesson_num,
            'available': len(session.lessons)
        }), 404

    if lesson.audio_generated and generate_audio:
        return jsonify({
            'message': 'Lesson already generated',
            'lesson': lesson.to_dict()
        }), 200

    # Generate lesson
    lesson = manager.generate_lesson(
        session_id=session_id,
        lesson_number=lesson_num,
        generate_audio=generate_audio,
        target_duration_minutes=target_duration
    )

    if lesson.generation_error:
        return jsonify({
            'error': 'Generation failed',
            'message': lesson.generation_error,
            'lesson': lesson.to_dict()
        }), 500

    return jsonify({
        'message': 'Lesson generated successfully',
        'lesson': lesson.to_dict()
    }), 201


@api_v2.route('/sessions/<session_id>/lessons/<int:lesson_num>/transcript', methods=['GET'])
@handle_errors
def get_transcript(session_id, lesson_num):
    """
    Get lesson transcript.

    Path Parameters:
        session_id: Session identifier
        lesson_num: Lesson number (1-indexed)

    Query Parameters:
        format: string (optional) - Output format: markdown, plain, srt (default: markdown)

    Returns:
        200: Transcript content
        404: Session, lesson, or transcript not found
    """
    format_type = request.args.get('format', 'markdown')

    if format_type not in ['markdown', 'plain', 'srt']:
        return jsonify({
            'error': 'Invalid format',
            'valid_values': ['markdown', 'plain', 'srt']
        }), 400

    manager = get_manager()
    transcript = manager.get_transcript(session_id, lesson_num, format_type)

    if not transcript:
        return jsonify({
            'error': 'Transcript not available',
            'message': 'Generate the lesson first',
            'hint': f'POST /api/v2/sessions/{session_id}/lessons/{lesson_num}/generate'
        }), 404

    # Return based on format
    if format_type == 'plain':
        return Response(transcript, mimetype='text/plain')
    elif format_type == 'srt':
        return Response(
            transcript,
            mimetype='text/plain',
            headers={'Content-Disposition': f'attachment; filename=lesson_{lesson_num}.srt'}
        )
    else:
        return jsonify({
            'session_id': session_id,
            'lesson_num': lesson_num,
            'format': format_type,
            'transcript': transcript
        }), 200


@api_v2.route('/sessions/<session_id>/lessons/<int:lesson_num>/audio', methods=['GET'])
@handle_errors
def get_audio(session_id, lesson_num):
    """
    Get audio URL for a lesson.

    Path Parameters:
        session_id: Session identifier
        lesson_num: Lesson number (1-indexed)

    Query Parameters:
        fresh: bool (optional) - Generate fresh presigned URL (default: true)

    Returns:
        200: Audio URL
        404: Audio not available
    """
    fresh = request.args.get('fresh', 'true').lower() == 'true'

    manager = get_manager()
    audio_url = manager.get_audio_url(session_id, lesson_num, fresh=fresh)

    if not audio_url:
        return jsonify({
            'error': 'Audio not available',
            'message': 'Generate the lesson with audio first',
            'hint': f'POST /api/v2/sessions/{session_id}/lessons/{lesson_num}/generate'
        }), 404

    lesson = manager.get_lesson(session_id, lesson_num)

    return jsonify({
        'session_id': session_id,
        'lesson_num': lesson_num,
        'audio_url': audio_url,
        'duration_seconds': lesson.actual_duration_seconds if lesson else 0
    }), 200


# =============================================================================
# Batch Operations
# =============================================================================

@api_v2.route('/sessions/<session_id>/generate-all', methods=['POST'])
@handle_errors
def generate_all_lessons(session_id):
    """
    Generate all lessons for a session.

    Path Parameters:
        session_id: Session identifier

    Request Body:
        generate_audio: bool (optional) - Generate audio for all (default: true)

    Returns:
        201: All lessons generated
        400: Session not ready
    """
    data = request.get_json() or {}
    generate_audio = data.get('generate_audio', True)

    manager = get_manager()
    session = manager.get_session(session_id)

    if not session:
        return jsonify({
            'error': 'Session not found',
            'session_id': session_id
        }), 404

    if session.status not in [SessionStatus.READY, SessionStatus.GENERATING]:
        return jsonify({
            'error': 'Session not ready',
            'status': session.status.value
        }), 400

    session = manager.generate_all_lessons(session_id, generate_audio=generate_audio)

    return jsonify({
        'message': 'All lessons generated',
        'session': session.to_dict()
    }), 201


# =============================================================================
# Admin Endpoints
# =============================================================================

@api_v2.route('/admin/cleanup', methods=['POST'])
@handle_errors
def cleanup_sessions():
    """
    Cleanup old sessions.

    Request Body:
        max_age_hours: int (optional) - Maximum session age (default: 24)

    Returns:
        200: Cleanup completed
    """
    data = request.get_json() or {}
    max_age_hours = data.get('max_age_hours', 24)

    manager = get_manager()
    removed = manager.cleanup_old_sessions(max_age_hours)

    return jsonify({
        'message': 'Cleanup completed',
        'sessions_removed': removed
    }), 200


# =============================================================================
# Register Blueprint Function
# =============================================================================

def register_v2_routes(app):
    """Register v2 API routes with Flask app."""
    app.register_blueprint(api_v2)
    logger.info("Registered v2 API routes")
