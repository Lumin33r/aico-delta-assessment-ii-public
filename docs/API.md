# AI Personal Tutor - API Reference

## Base URL

- **Local Development:** `http://localhost:8000`
- **Production:** Your ALB DNS name from Terraform outputs

## API Versions

- **v1 (Legacy):** `/api/*` - Original endpoints
- **v2 (Recommended):** `/api/v2/*` - Enhanced session management

---

# API v1 Reference (Legacy)

## Endpoints

### Health Check

```
GET /health
```

Returns the health status of the backend service.

**Response:**

```json
{
  "status": "healthy",
  "ollama": "connected",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### Root

```
GET /
```

Returns API information and available endpoints.

**Response:**

```json
{
  "name": "AI Personal Tutor API",
  "version": "1.0.0",
  "endpoints": {
    "POST /api/ingest": "Ingest content from URL",
    "GET /api/session": "Get current session info",
    "DELETE /api/session": "Clear current session",
    "GET /api/lesson/{num}/audio": "Get audio URL for lesson"
  }
}
```

---

### Ingest Content

```
POST /api/ingest
```

Extracts content from a URL and generates a lesson plan.

**Request Body:**

```json
{
  "url": "https://example.com/article",
  "session_id": "optional-session-id"
}
```

**Response:**

```json
{
  "session_id": "uuid-v4",
  "lesson_plan": {
    "title": "Understanding AWS Lambda",
    "source_url": "https://example.com/article",
    "topics": [
      "What is serverless computing",
      "Lambda function basics",
      "Event-driven architecture",
      "Best practices"
    ],
    "estimated_episodes": 4,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

**Errors:**

- `400 Bad Request` - Missing URL or invalid URL format
- `422 Unprocessable Entity` - Could not extract content from URL
- `500 Internal Server Error` - Ollama or processing error

---

### Get Session

```
GET /api/session
```

Retrieves the current tutoring session information.

**Query Parameters:**

- `session_id` (required): The session identifier

**Response:**

```json
{
  "session_id": "uuid-v4",
  "lesson_plan": {
    "title": "Understanding AWS Lambda",
    "topics": ["Topic 1", "Topic 2", "Topic 3"],
    "estimated_episodes": 3
  },
  "completed_lessons": [1, 2],
  "current_lesson": 3,
  "progress_percent": 66.7
}
```

**Errors:**

- `400 Bad Request` - Missing session_id
- `404 Not Found` - Session not found

---

### Clear Session

```
DELETE /api/session
```

Clears the current session and all generated content.

**Query Parameters:**

- `session_id` (required): The session identifier

**Response:**

```json
{
  "message": "Session cleared",
  "session_id": "uuid-v4"
}
```

---

### Get Lesson Audio

```
GET /api/lesson/{num}/audio
```

Generates or retrieves the podcast audio for a specific lesson.

**Path Parameters:**

- `num` (required): Lesson number (1-indexed)

**Query Parameters:**

- `session_id` (required): The session identifier

**Response:**

```json
{
  "lesson_number": 1,
  "title": "What is serverless computing",
  "audio_url": "https://s3.amazonaws.com/bucket/presigned-url",
  "transcript": [
    {
      "speaker": "Alex",
      "text": "Hey Sam! Today we're diving into serverless computing."
    },
    {
      "speaker": "Sam",
      "text": "Sounds exciting! But wait, if it's serverless, where does the code run?"
    }
  ],
  "duration_seconds": 180
}
```

**Errors:**

- `400 Bad Request` - Missing session_id
- `404 Not Found` - Session or lesson not found
- `500 Internal Server Error` - Audio generation error

---

# API v2 Reference (Recommended)

The v2 API provides improved session management with separate endpoints for session and lesson operations.

## Base URL

- **Local Development:** `http://localhost:8000/api/v2`
- **Production:** `{ALB_DNS}/api/v2`

---

## Session Endpoints

### Create Session

```
POST /api/v2/sessions
```

Creates a new tutoring session from a URL. Extracts content, processes it, and generates a lesson plan.

**Request Body:**

```json
{
  "url": "https://example.com/python-tutorial"
}
```

**Response (201 Created):**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://example.com/python-tutorial",
  "status": "ready",
  "content_title": "Python Tutorial",
  "created_at": "2024-01-15T10:30:00Z",
  "lessons": [
    {
      "lesson_number": 1,
      "title": "Getting Started with Python",
      "description": "Introduction to Python programming",
      "topics": ["Variables", "Data Types"],
      "estimated_duration_minutes": 10,
      "generated": false
    }
  ]
}
```

**Errors:**

- `400 Bad Request` - Missing or invalid URL
- `422 Unprocessable Entity` - Could not extract/process content
- `500 Internal Server Error` - Server error

---

### List Sessions

```
GET /api/v2/sessions
```

Lists all sessions with optional filtering.

**Query Parameters:**

- `status` (optional): Filter by status (`created`, `ready`, `complete`, `error`)
- `limit` (optional): Maximum number of sessions to return (default: 50)

**Response (200 OK):**

```json
{
  "sessions": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "url": "https://example.com/tutorial",
      "status": "ready",
      "content_title": "Python Tutorial",
      "lesson_count": 3,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

---

### Get Session

```
GET /api/v2/sessions/{session_id}
```

Retrieves detailed information about a specific session.

**Path Parameters:**

- `session_id` (required): The session identifier

**Response (200 OK):**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://example.com/tutorial",
  "status": "ready",
  "content_title": "Python Tutorial",
  "created_at": "2024-01-15T10:30:00Z",
  "lessons": {
    "1": {
      "lesson_number": 1,
      "title": "Getting Started",
      "description": "Introduction to Python",
      "topics": ["Variables", "Types"],
      "estimated_duration_minutes": 10,
      "generated": true,
      "audio_path": "s3://bucket/session/lesson_1.mp3"
    }
  }
}
```

**Errors:**

- `404 Not Found` - Session not found

---

### Delete Session

```
DELETE /api/v2/sessions/{session_id}
```

Deletes a session and all associated resources.

**Path Parameters:**

- `session_id` (required): The session identifier

**Response (200 OK):**

```json
{
  "success": true,
  "message": "Session deleted",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Errors:**

- `404 Not Found` - Session not found

---

## Lesson Endpoints

### List Lessons

```
GET /api/v2/sessions/{session_id}/lessons
```

Lists all lessons for a session.

**Response (200 OK):**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "lessons": [
    {
      "lesson_number": 1,
      "title": "Getting Started",
      "description": "Introduction",
      "topics": ["Topic 1"],
      "estimated_duration_minutes": 10,
      "generated": false
    }
  ],
  "total": 3
}
```

---

### Get Lesson

```
GET /api/v2/sessions/{session_id}/lessons/{lesson_number}
```

Gets details for a specific lesson.

**Path Parameters:**

- `session_id`: Session identifier
- `lesson_number`: Lesson number (1-indexed)

**Response (200 OK):**

```json
{
  "lesson_number": 1,
  "title": "Getting Started with Python",
  "description": "Introduction to Python programming",
  "topics": ["Variables", "Data Types", "Basic Operations"],
  "estimated_duration_minutes": 10,
  "generated": true,
  "script": {
    "title": "Getting Started with Python",
    "total_turns": 24,
    "segments": ["intro", "discussion", "outro"]
  },
  "audio_path": "s3://bucket/session/lesson_1.mp3"
}
```

---

### Generate Lesson

```
POST /api/v2/sessions/{session_id}/lessons/{lesson_number}/generate
```

Generates the script and audio for a specific lesson.

**Request Body (optional):**

```json
{
  "skip_audio": false,
  "voice_config": {
    "alex": "Matthew",
    "sam": "Joanna"
  }
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "lesson_number": 1,
  "script": {
    "title": "Getting Started with Python",
    "total_turns": 24,
    "estimated_duration_minutes": 10
  },
  "audio": {
    "audio_path": "s3://bucket/session/lesson_1.mp3",
    "duration_seconds": 600,
    "file_size_bytes": 1024000
  },
  "generation_time_seconds": 45.2
}
```

**Errors:**

- `404 Not Found` - Session or lesson not found
- `400 Bad Request` - Invalid lesson number
- `500 Internal Server Error` - Generation error

---

### Get Transcript

```
GET /api/v2/sessions/{session_id}/lessons/{lesson_number}/transcript
```

Gets the transcript for a generated lesson.

**Query Parameters:**

- `format` (optional): `markdown` (default), `plain`, or `srt`

**Response (200 OK):**

```json
{
  "lesson_number": 1,
  "format": "markdown",
  "transcript": "# Getting Started with Python\n\n**Alex:** Welcome to Python basics!\n\n**Sam:** I'm excited to learn!"
}
```

**Errors:**

- `404 Not Found` - Lesson not generated yet

---

### Get Audio URL

```
GET /api/v2/sessions/{session_id}/lessons/{lesson_number}/audio
```

Gets the audio URL for a generated lesson.

**Response (200 OK):**

```json
{
  "lesson_number": 1,
  "audio_url": "https://s3.amazonaws.com/bucket/presigned-url",
  "duration_seconds": 600,
  "expires_in_seconds": 3600
}
```

---

## Batch Operations

### Generate All Lessons

```
POST /api/v2/sessions/{session_id}/generate-all
```

Generates all lessons for a session in sequence.

**Request Body (optional):**

```json
{
  "skip_audio": false,
  "parallel": false
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "results": {
    "1": { "success": true, "duration_seconds": 45.2 },
    "2": { "success": true, "duration_seconds": 52.1 },
    "3": { "success": true, "duration_seconds": 38.9 }
  },
  "total_time_seconds": 136.2
}
```

---

## Admin Endpoints

### Cleanup Sessions

```
POST /api/v2/admin/cleanup
```

Removes old or expired sessions.

**Request Body:**

```json
{
  "max_age_hours": 24,
  "status": ["error"]
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "deleted_count": 5,
  "remaining_count": 10
}
```

---

## Session Status Values

| Status       | Description                        |
| ------------ | ---------------------------------- |
| `created`    | Session created, not yet processed |
| `validating` | Validating URL                     |
| `extracting` | Extracting content from URL        |
| `processing` | Processing content                 |
| `planning`   | Generating lesson plan             |
| `ready`      | Ready for lesson generation        |
| `generating` | Generating lesson content          |
| `complete`   | All lessons generated              |
| `error`      | Error occurred                     |

---

## Error Response Format

All v2 errors follow this format:

```json
{
  "error": "ErrorType",
  "message": "Human-readable description",
  "code": "ERR_CODE",
  "details": {
    "field": "value"
  }
}
```

**Common Error Codes:**

- `ERR_MISSING_URL` - URL not provided
- `ERR_INVALID_URL` - Invalid URL format
- `ERR_SESSION_NOT_FOUND` - Session doesn't exist
- `ERR_LESSON_NOT_FOUND` - Lesson doesn't exist
- `ERR_NOT_GENERATED` - Lesson hasn't been generated yet
- `ERR_EXTRACTION_FAILED` - Content extraction failed
- `ERR_GENERATION_FAILED` - Script/audio generation failed

---

## Rate Limiting

The API does not currently implement rate limiting, but production deployments should consider:

- Limiting `/api/ingest` and `/api/v2/sessions` to prevent abuse
- Caching generated audio to reduce Polly costs
- Implementing request throttling for expensive operations

## Authentication

The current implementation does not require authentication. For production:

1. Implement API key authentication
2. Use AWS Cognito for user sessions
3. Add JWT validation middleware

## CORS Configuration

The backend allows CORS from all origins during development. For production, configure specific allowed origins in the Flask app.
