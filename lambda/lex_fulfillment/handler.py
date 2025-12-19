"""
Lex Fulfillment Lambda Handler

This Lambda function handles fulfillment requests from Amazon Lex V2.
It connects the Lex bot to the AI Tutor backend API for:
- Creating lesson plans from URLs
- Starting lessons
- Managing session state

Lex V2 Event Structure:
{
    "sessionId": "...",
    "inputTranscript": "...",
    "interpretations": [...],
    "sessionState": {
        "intent": {
            "name": "...",
            "slots": {...},
            "state": "..."
        },
        "sessionAttributes": {...}
    }
}
"""

import json
import os
import logging
from urllib import request, error
from urllib.parse import urljoin

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))

# Backend API URL from environment
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')


def lambda_handler(event, context):
    """
    Main Lambda handler for Lex V2 fulfillment.

    Args:
        event: Lex V2 event
        context: Lambda context

    Returns:
        Lex V2 response
    """
    logger.info(f"Received event: {json.dumps(event)}")

    # Extract intent information
    intent_name = event['sessionState']['intent']['name']
    slots = event['sessionState']['intent'].get('slots', {})
    session_attributes = event['sessionState'].get('sessionAttributes', {}) or {}
    session_id = event.get('sessionId', '')
    input_transcript = event.get('inputTranscript', '')

    logger.info(f"Intent: {intent_name}, Slots: {slots}, Input: {input_transcript}")

    # Route to appropriate handler
    # Map Terraform intent names to handlers
    handlers = {
        'CreateLessonPlan': handle_create_lesson_plan,
        'ProvideURLIntent': handle_provide_url,  # Terraform intent name
        'StartLesson': handle_start_lesson,
        'StartLessonIntent': handle_start_lesson,  # Terraform intent name
        'WelcomeIntent': handle_welcome,
        'HelpIntent': handle_help,
        'GetHelpIntent': handle_help,  # Terraform intent name
        'NextLessonIntent': handle_next_lesson,
        'RepeatLessonIntent': handle_repeat_lesson,
        'GetProgressIntent': handle_get_progress,
        'CheckStatusIntent': handle_check_status,  # New async status check
        'FallbackIntent': handle_fallback,
    }

    handler = handlers.get(intent_name, handle_fallback)

    try:
        response = handler(event, slots, session_attributes)
        logger.info(f"Response: {json.dumps(response)}")
        return response
    except Exception as e:
        logger.error(f"Handler error: {str(e)}", exc_info=True)
        return build_response(
            event,
            session_attributes,
            "I encountered an error processing your request. Please try again.",
            close_intent=True
        )


def handle_create_lesson_plan(event, slots, session_attributes):
    """
    Handle CreateLessonPlan intent - creates lessons from a URL.
    """
    # Extract URL from slot
    url_slot = slots.get('SourceURL', {})
    url = url_slot.get('value', {}).get('interpretedValue') if url_slot else None

    if not url:
        # Elicit the URL slot
        return build_elicit_slot_response(
            event,
            session_attributes,
            'SourceURL',
            "What URL would you like me to create lessons from? Please paste the full web address."
        )

    # Call backend API
    logger.info(f"Creating lesson plan for URL: {url}")

    try:
        api_response = call_backend_api('/api/lex/create-lesson', {
            'url': url,
            'user_id': event.get('sessionId', 'anonymous')
        })

        if api_response.get('success'):
            # Store session ID in attributes
            session_attributes['tutor_session_id'] = api_response.get('session_id', '')
            session_attributes['lessons'] = json.dumps(api_response.get('lessons', []))

            message = api_response.get('message',
                "I've created your lessons! Would you like to start with lesson 1?")

            return build_response(
                event,
                session_attributes,
                message,
                close_intent=True
            )
        else:
            return build_response(
                event,
                session_attributes,
                api_response.get('message', "I had trouble creating lessons from that URL. Please try a different one."),
                close_intent=True
            )

    except Exception as e:
        logger.error(f"Backend API error: {str(e)}")
        return build_response(
            event,
            session_attributes,
            "I couldn't connect to the lesson service. Please try again in a moment.",
            close_intent=True
        )


def handle_provide_url(event, slots, session_attributes):
    """
    Handle ProvideURLIntent - user provides a URL to learn from.
    Extracts URL from the user's input transcript since we don't have a slot.
    Uses async processing to avoid Lex timeout.
    """
    import re

    # Get the user's input
    input_transcript = event.get('inputTranscript', '')

    # Try to extract URL from the input
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, input_transcript)

    url = urls[0] if urls else None

    if not url:
        # No URL found in input, ask for one
        return build_response(
            event,
            session_attributes,
            "I'd be happy to create lessons for you! Please paste the full URL you'd like me to learn from (starting with http:// or https://).",
            close_intent=True
        )

    # Call backend API - use async endpoint to avoid timeout
    logger.info(f"Creating lesson plan (async) for URL: {url}")
    user_id = event.get('sessionId', 'anonymous')

    try:
        api_response = call_backend_api('/api/lex/create-lesson-async', {
            'url': url,
            'user_id': user_id
        })

        if api_response.get('success'):
            # Store session ID in attributes for later lookup
            session_attributes['tutor_session_id'] = api_response.get('session_id', '')
            session_attributes['processing_url'] = url

            message = api_response.get('message',
                "I'm creating your lessons now. This takes about a minute. Say 'check status' when you're ready!")

            return build_response(
                event,
                session_attributes,
                message,
                close_intent=True
            )
        else:
            return build_response(
                event,
                session_attributes,
                api_response.get('message', "I had trouble starting lesson creation. Please try again."),
                close_intent=True
            )

    except Exception as e:
        logger.error(f"Backend API error: {str(e)}")
        return build_response(
            event,
            session_attributes,
            "I couldn't connect to the lesson service. Please try again in a moment.",
            close_intent=True
        )


def handle_check_status(event, slots, session_attributes):
    """
    Handle CheckStatusIntent - check if lessons are ready.
    """
    tutor_session_id = session_attributes.get('tutor_session_id', '')
    user_id = event.get('sessionId', 'anonymous')

    if not tutor_session_id:
        return build_response(
            event,
            session_attributes,
            "I don't have any lessons in progress. Share a URL to get started!",
            close_intent=True
        )

    try:
        api_response = call_backend_api('/api/lex/session-status', {
            'session_id': tutor_session_id,
            'user_id': user_id
        })

        status = api_response.get('status', 'unknown')
        
        if status == 'ready':
            # Lessons are ready - update session attributes
            session_attributes['lessons'] = json.dumps(api_response.get('lessons', []))
            
        message = api_response.get('message', "I'm still working on your lessons...")
        
        return build_response(
            event,
            session_attributes,
            message,
            close_intent=True
        )

    except Exception as e:
        logger.error(f"Backend API error: {str(e)}")
        return build_response(
            event,
            session_attributes,
            "I couldn't check the status. Please try again in a moment.",
            close_intent=True
        )


def handle_start_lesson(event, slots, session_attributes):
    """
    Handle StartLesson intent - starts a specific lesson.
    """
    # Get session ID from attributes
    tutor_session_id = session_attributes.get('tutor_session_id', '')

    if not tutor_session_id:
        return build_response(
            event,
            session_attributes,
            "I don't have any lessons ready yet. Would you like to create some? Just share a URL with me!",
            close_intent=True
        )

    # Get lesson number from slot (default to 1)
    lesson_slot = slots.get('LessonNumber', {})
    lesson_num = 1

    if lesson_slot and lesson_slot.get('value'):
        try:
            lesson_num = int(lesson_slot['value']['interpretedValue'])
        except (ValueError, KeyError):
            lesson_num = 1

    logger.info(f"Starting lesson {lesson_num} for session {tutor_session_id}")

    try:
        api_response = call_backend_api('/api/lex/start-lesson', {
            'session_id': tutor_session_id,
            'lesson_number': lesson_num
        })

        if api_response.get('success'):
            message = api_response.get('message', f"Starting lesson {lesson_num}...")

            # If audio needs generation, let user know
            if api_response.get('needs_generation'):
                message = f"I'm preparing lesson {lesson_num}. Alex and Sam are getting ready to record. This will take about 30 seconds..."

            return build_response(
                event,
                session_attributes,
                message,
                close_intent=True,
                response_card=build_audio_card(api_response) if api_response.get('audio_url') else None
            )
        else:
            return build_response(
                event,
                session_attributes,
                api_response.get('message', "I couldn't start that lesson. Please try again."),
                close_intent=True
            )

    except Exception as e:
        logger.error(f"Backend API error: {str(e)}")
        return build_response(
            event,
            session_attributes,
            "I couldn't start the lesson. Please try again.",
            close_intent=True
        )


def handle_welcome(event, slots, session_attributes):
    """
    Handle WelcomeIntent - greet the user.
    """
    message = (
        "Welcome to AI Tutor! 🎓 I'm here to help you learn from any web content. "
        "Just share a URL with me, and I'll create personalized podcast-style lessons "
        "with two AI hosts - Alex and Sam - who will explain the concepts in an engaging way.\n\n"
        "Ready to start? Just paste a URL!"
    )

    return build_response(
        event,
        session_attributes,
        message,
        close_intent=True
    )


def handle_help(event, slots, session_attributes):
    """
    Handle HelpIntent - provide usage instructions.
    """
    message = (
        "Here's how I can help:\n\n"
        "1️⃣ **Share a URL** - Paste any webpage link and I'll create lessons from it\n"
        "2️⃣ **Start a lesson** - Say 'start lesson 1' to begin learning\n"
        "3️⃣ **Ask questions** - I'm here to help you understand the content\n\n"
        "The lessons are presented as conversations between Alex (the expert) and Sam "
        "(the curious learner). Ready to try? Just paste a URL!"
    )

    return build_response(
        event,
        session_attributes,
        message,
        close_intent=True
    )


def handle_next_lesson(event, slots, session_attributes):
    """
    Handle NextLessonIntent - move to the next lesson.
    """
    tutor_session_id = session_attributes.get('tutor_session_id', '')

    if not tutor_session_id:
        return build_response(
            event,
            session_attributes,
            "I don't have any lessons ready yet. Share a URL with me and I'll create some lessons for you!",
            close_intent=True
        )

    try:
        api_response = call_backend_api('/api/lex/next-lesson', {
            'session_id': tutor_session_id
        })

        if api_response.get('success'):
            message = api_response.get('message', "Moving to the next lesson...")
            return build_response(
                event,
                session_attributes,
                message,
                close_intent=True
            )
        else:
            return build_response(
                event,
                session_attributes,
                api_response.get('message', "There are no more lessons. You've completed all of them! 🎉"),
                close_intent=True
            )
    except Exception as e:
        logger.error(f"Backend API error: {str(e)}")
        return build_response(
            event,
            session_attributes,
            "I couldn't get the next lesson. Please try again.",
            close_intent=True
        )


def handle_repeat_lesson(event, slots, session_attributes):
    """
    Handle RepeatLessonIntent - repeat the current lesson.
    """
    tutor_session_id = session_attributes.get('tutor_session_id', '')

    if not tutor_session_id:
        return build_response(
            event,
            session_attributes,
            "I don't have any lessons ready yet. Share a URL with me and I'll create some lessons for you!",
            close_intent=True
        )

    try:
        api_response = call_backend_api('/api/lex/repeat-lesson', {
            'session_id': tutor_session_id
        })

        if api_response.get('success'):
            message = api_response.get('message', "Let me play that lesson again...")
            return build_response(
                event,
                session_attributes,
                message,
                close_intent=True
            )
        else:
            return build_response(
                event,
                session_attributes,
                api_response.get('message', "I couldn't repeat the lesson. Please try again."),
                close_intent=True
            )
    except Exception as e:
        logger.error(f"Backend API error: {str(e)}")
        return build_response(
            event,
            session_attributes,
            "I couldn't repeat the lesson. Please try again.",
            close_intent=True
        )


def handle_get_progress(event, slots, session_attributes):
    """
    Handle GetProgressIntent - show learning progress.
    """
    tutor_session_id = session_attributes.get('tutor_session_id', '')

    if not tutor_session_id:
        return build_response(
            event,
            session_attributes,
            "You haven't started any lessons yet. Share a URL with me to get started!",
            close_intent=True
        )

    try:
        api_response = call_backend_api('/api/lex/progress', {
            'session_id': tutor_session_id
        })

        if api_response.get('success'):
            message = api_response.get('message', "Here's your progress...")
            return build_response(
                event,
                session_attributes,
                message,
                close_intent=True
            )
        else:
            return build_response(
                event,
                session_attributes,
                api_response.get('message', "I couldn't get your progress. Please try again."),
                close_intent=True
            )
    except Exception as e:
        logger.error(f"Backend API error: {str(e)}")
        return build_response(
            event,
            session_attributes,
            "I couldn't get your progress. Please try again.",
            close_intent=True
        )


def handle_fallback(event, slots, session_attributes):
    """
    Handle FallbackIntent - respond to unrecognized input.
    """
    message = (
        "I didn't quite catch that. You can:\n"
        "• Share a URL to create lessons\n"
        "• Say 'start lesson 1' to begin learning\n"
        "• Say 'help' for more options"
    )

    return build_response(
        event,
        session_attributes,
        message,
        close_intent=True
    )


# =============================================================================
# Helper Functions
# =============================================================================

def call_backend_api(endpoint: str, data: dict) -> dict:
    """
    Call the backend API.

    Args:
        endpoint: API endpoint path
        data: Request body data

    Returns:
        API response as dict
    """
    url = urljoin(BACKEND_URL, endpoint)

    req = request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        method='POST'
    )

    try:
        with request.urlopen(req, timeout=90) as response:
            return json.loads(response.read().decode('utf-8'))
    except error.HTTPError as e:
        body = e.read().decode('utf-8')
        logger.error(f"HTTP Error {e.code}: {body}")
        try:
            return json.loads(body)
        except:
            return {'success': False, 'message': f'API error: {e.code}'}
    except error.URLError as e:
        logger.error(f"URL Error: {e.reason}")
        return {'success': False, 'message': 'Could not connect to backend'}


def build_response(event, session_attributes, message, close_intent=False, response_card=None):
    """
    Build a Lex V2 response.
    """
    intent = event['sessionState']['intent']

    response = {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Close' if close_intent else 'Delegate'
            },
            'intent': {
                'name': intent['name'],
                'slots': intent.get('slots', {}),
                'state': 'Fulfilled' if close_intent else 'InProgress'
            }
        },
        'messages': [
            {
                'contentType': 'PlainText',
                'content': message
            }
        ]
    }

    if response_card:
        response['messages'].append(response_card)

    return response


def build_elicit_slot_response(event, session_attributes, slot_name, message):
    """
    Build a response that elicits a specific slot.
    """
    intent = event['sessionState']['intent']

    return {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'ElicitSlot',
                'slotToElicit': slot_name
            },
            'intent': {
                'name': intent['name'],
                'slots': intent.get('slots', {}),
                'state': 'InProgress'
            }
        },
        'messages': [
            {
                'contentType': 'PlainText',
                'content': message
            }
        ]
    }


def build_audio_card(api_response):
    """
    Build a response card with audio player link.
    """
    audio_url = api_response.get('audio_url', '')

    if not audio_url:
        return None

    return {
        'contentType': 'ImageResponseCard',
        'imageResponseCard': {
            'title': '🎧 Your Lesson is Ready!',
            'subtitle': 'Click to listen to Alex and Sam',
            'buttons': [
                {
                    'text': '▶️ Play Lesson',
                    'value': 'play audio'
                }
            ]
        }
    }
