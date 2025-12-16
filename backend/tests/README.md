# Backend Tests

This directory contains **136 unit and integration tests** for the AI Personal Tutor backend.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Test Structure](#test-structure)
- [Test Files Overview](#test-files-overview)
  - [test_content_extraction.py (30 tests)](#test_content_extractionpy-30-tests)
  - [test_podcast_generation.py (38 tests)](#test_podcast_generationpy-38-tests)
  - [test_audio_synthesis.py (45 tests)](#test_audio_synthesispy-45-tests)
  - [test_integration.py (23 tests)](#test_integrationpy-23-tests)
- [Test Classes Explained](#test-classes-explained)
- [Running Tests](#running-tests)
- [Test Coverage](#test-coverage)
- [Testing Patterns Used](#testing-patterns-used)
- [Adding New Tests](#adding-new-tests)

---

## Quick Start

```bash
# From backend directory
cd backend
source .venv/bin/activate

# Run all 136 tests
PYTHONPATH=src pytest tests/ -v

# Run with coverage report
PYTHONPATH=src pytest tests/ --cov=src --cov-report=html
```

---

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                  # Shared pytest fixtures
├── test_content_extraction.py   # 30 tests - Web scraping & caching
├── test_podcast_generation.py   # 38 tests - LLM prompts & scripts
├── test_audio_synthesis.py      # 45 tests - Polly & audio stitching
└── test_integration.py          # 23 tests - Session manager & API routes
```

| File                                                              | Test Count | Primary Focus                              |
| ----------------------------------------------------------------- | ---------- | ------------------------------------------ |
| [test_content_extraction.py](#test_content_extractionpy-30-tests) | 30         | Web scraping, URL validation, caching      |
| [test_podcast_generation.py](#test_podcast_generationpy-38-tests) | 38         | LLM prompts, dialogue scripts, SSML        |
| [test_audio_synthesis.py](#test_audio_synthesispy-45-tests)       | 45         | AWS Polly, audio stitching, coordination   |
| [test_integration.py](#test_integrationpy-23-tests)               | 23         | Session CRUD, API endpoints, health checks |
| **Total**                                                         | **136**    |                                            |

---

## Test Files Overview

### test_content_extraction.py (30 tests)

Tests the web content extraction pipeline - from fetching URLs to processing and caching content.

#### Test Classes

| Class                  | Tests | What It Tests                                           |
| ---------------------- | ----- | ------------------------------------------------------- |
| `TestContentExtractor` | 5     | HTML parsing, script removal, network errors            |
| `TestContentProcessor` | 7     | Text chunking, topic extraction, code detection         |
| `TestURLValidator`     | 9     | URL format validation, normalization, domain extraction |
| `TestContentCache`     | 8     | LRU cache, expiration, eviction, stats                  |
| `TestIntegration`      | 1     | Full extraction pipeline                                |

#### Key Tests Explained

```python
# Tests that HTML scripts are stripped (security)
def test_extract_removes_script_tags():
    html = "<script>alert('xss')</script><p>Safe</p>"
    result = extractor.extract(html)
    assert "alert" not in result
    assert "Safe" in result

# Tests URL normalization
def test_normalize_url():
    assert normalize("example.com") == "https://example.com"
    assert normalize("HTTP://EXAMPLE.COM") == "https://example.com"

# Tests LRU cache eviction
def test_lru_eviction():
    cache = ContentCache(max_entries=2)
    cache.set("a", "1")
    cache.set("b", "2")
    cache.set("c", "3")  # Should evict "a"
    assert cache.get("a") is None
    assert cache.get("c") == "3"
```

---

### test_podcast_generation.py (38 tests)

Tests the LLM-powered podcast script generation - from prompts to formatted dialogue.

#### Test Classes

| Class                     | Tests | What It Tests                                  |
| ------------------------- | ----- | ---------------------------------------------- |
| `TestSpeaker`             | 4     | Speaker enum values, voices, roles             |
| `TestDialogueTurn`        | 4     | Word count, duration estimation, serialization |
| `TestEpisodeScript`       | 6     | Script structure, speaker balance, transcripts |
| `TestValidateScript`      | 2     | Script validation rules                        |
| `TestConversationPattern` | 2     | Dialogue patterns (explain, analogy)           |
| `TestScriptFormatter`     | 5     | SSML formatting, emphasis, pauses, SRT         |
| `TestPromptTemplates`     | 5     | LLM prompt construction                        |
| `TestPodcastGenerator`    | 9     | Ollama integration, JSON parsing, health       |
| `TestIntegration`         | 1     | Full formatting pipeline                       |

#### Key Tests Explained

````python
# Tests speaker voice mapping
def test_speaker_voice_id():
    assert Speaker.ALEX.voice_id == "Matthew"
    assert Speaker.SAM.voice_id == "Joanna"

# Tests dialogue turn duration estimation (150 WPM)
def test_estimated_duration():
    turn = DialogueTurn(speaker=Speaker.ALEX, text="One two three")
    assert turn.estimated_duration == 3 / 150 * 60  # ~1.2 seconds

# Tests SSML formatting for Polly
def test_format_turn_ssml():
    turn = DialogueTurn(speaker=Speaker.ALEX, text="Hello!")
    ssml = formatter.format_turn_ssml(turn)
    assert "<speak>" in ssml
    assert "Hello!" in ssml

# Tests LLM JSON response parsing (handles markdown blocks)
def test_parse_json_response_with_markdown():
    response = '```json\n{"title": "Test"}\n```'
    result = generator.parse_json_response(response)
    assert result == {"title": "Test"}
````

---

### test_audio_synthesis.py (45 tests)

Tests AWS Polly integration, audio stitching, and the synthesis coordinator.

#### Test Classes

| Class                          | Tests | What It Tests                          |
| ------------------------------ | ----- | -------------------------------------- |
| `TestStitchConfig`             | 2     | Audio stitching configuration          |
| `TestAudioChunk`               | 1     | Audio chunk data structure             |
| `TestAudioStitcher`            | 7     | Audio concatenation, pauses, duration  |
| `TestSilenceCreation`          | 2     | Silence generation for pauses          |
| `TestVoiceConfig`              | 4     | Polly voice configuration              |
| `TestSynthesisConfig`          | 2     | Synthesis settings (region, format)    |
| `TestSynthesisResult`          | 2     | Result dataclass, serialization        |
| `TestSynthesisProgress`        | 2     | Progress tracking, percentages         |
| `TestEnhancedAudioSynthesizer` | 8     | Polly client, caching, cost estimation |
| `TestJobStatus`                | 1     | Job status enum                        |
| `TestSynthesisJob`             | 2     | Job tracking, serialization            |
| `TestBatchResult`              | 2     | Batch processing results               |
| `TestAudioCoordinator`         | 8     | Orchestration, callbacks, cleanup      |
| `TestIntegration`              | 2     | Full synthesis pipeline                |

#### Key Tests Explained

```python
# Tests default AWS region is us-west-2
def test_default_config():
    config = SynthesisConfig()
    assert config.region == 'us-west-2'
    assert config.output_format == 'mp3'

# Tests pause calculation between speakers
def test_calculate_pause_different_speakers():
    pause = stitcher.calculate_pause(
        prev_speaker="Alex",
        curr_speaker="Sam"
    )
    assert pause == 400  # 400ms between different speakers

# Tests synthesis cost estimation
def test_estimate_cost():
    # Polly charges $4 per 1M characters (neural)
    cost = synthesizer.estimate_cost(characters=1000)
    assert cost == 0.004  # $0.004 for 1000 chars

# Tests old job cleanup
def test_cleanup_old_jobs():
    coordinator.add_job(old_job)  # 48 hours old
    coordinator.add_job(new_job)  # Just created
    coordinator.cleanup_old_jobs(max_age_hours=24)
    assert old_job not in coordinator.jobs
    assert new_job in coordinator.jobs
```

---

### test_integration.py (23 tests)

Tests the session manager and API routes - the glue that connects everything.

#### Test Classes

| Class                     | Tests | What It Tests                              |
| ------------------------- | ----- | ------------------------------------------ |
| `TestTutorSessionManager` | 10    | Session CRUD, lesson generation, health    |
| `TestSessionData`         | 5     | Data models (LessonInfo, TutorSessionData) |
| `TestHelperFunctions`     | 1     | Manager singleton pattern                  |
| `TestAPIv2Routes`         | 7     | HTTP endpoints, status codes, errors       |

#### Key Tests Explained

```python
# Tests session creation
def test_create_session_success(mock_extractor, mock_generator):
    manager = TutorSessionManager()
    session = manager.create_session("https://example.com")
    assert session.id is not None
    assert session.url == "https://example.com"
    assert session.status == SessionStatus.READY

# Tests 404 for non-existent session
def test_get_session_not_found():
    manager = TutorSessionManager()
    with pytest.raises(SessionNotFoundError):
        manager.get_session("fake-id-12345")

# Tests DELETE returns 204 No Content
def test_delete_session_endpoint(client):
    # Create then delete
    create_response = client.post('/api/v2/sessions',
        json={'url': 'https://example.com'})
    session_id = create_response.json['id']

    delete_response = client.delete(f'/api/v2/sessions/{session_id}')
    assert delete_response.status_code == 204

# Tests health endpoint
def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'
```

---

## Test Classes Explained

### What Each Class Tests

| Service Layer | Test Class                     | Source File                                  |
| ------------- | ------------------------------ | -------------------------------------------- |
| **Content**   | `TestContentExtractor`         | `src/services/content_extractor.py`          |
| **Content**   | `TestContentProcessor`         | `src/services/content_processor.py`          |
| **Content**   | `TestURLValidator`             | `src/utils/url_validator.py`                 |
| **Content**   | `TestContentCache`             | `src/utils/cache.py`                         |
| **Podcast**   | `TestSpeaker`                  | `src/models/dialogue.py`                     |
| **Podcast**   | `TestDialogueTurn`             | `src/models/dialogue.py`                     |
| **Podcast**   | `TestEpisodeScript`            | `src/models/dialogue.py`                     |
| **Podcast**   | `TestScriptFormatter`          | `src/services/script_formatter.py`           |
| **Podcast**   | `TestPodcastGenerator`         | `src/services/podcast_generator.py`          |
| **Audio**     | `TestAudioStitcher`            | `src/services/audio_stitcher.py`             |
| **Audio**     | `TestEnhancedAudioSynthesizer` | `src/services/enhanced_audio_synthesizer.py` |
| **Audio**     | `TestAudioCoordinator`         | `src/services/audio_coordinator.py`          |
| **API**       | `TestTutorSessionManager`      | `src/services/tutor_session_manager.py`      |
| **API**       | `TestAPIv2Routes`              | `src/app.py`                                 |

---

## Running Tests

### Run All Tests

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=src pytest tests/ -v
```

### Run Specific File

```bash
# Content extraction tests only
PYTHONPATH=src pytest tests/test_content_extraction.py -v

# Podcast generation tests only
PYTHONPATH=src pytest tests/test_podcast_generation.py -v

# Audio synthesis tests only
PYTHONPATH=src pytest tests/test_audio_synthesis.py -v

# Integration tests only
PYTHONPATH=src pytest tests/test_integration.py -v
```

### Run Specific Class

```bash
# All URL validator tests
PYTHONPATH=src pytest tests/test_content_extraction.py::TestURLValidator -v

# All audio stitcher tests
PYTHONPATH=src pytest tests/test_audio_synthesis.py::TestAudioStitcher -v
```

### Run Specific Test

```bash
PYTHONPATH=src pytest tests/test_content_extraction.py::TestURLValidator::test_normalize_url -v
```

### Run with Verbosity Options

```bash
# Minimal output
PYTHONPATH=src pytest tests/ -q

# Show local variables on failure
PYTHONPATH=src pytest tests/ -v --tb=long

# Stop on first failure
PYTHONPATH=src pytest tests/ -x

# Show slowest 10 tests
PYTHONPATH=src pytest tests/ --durations=10
```

---

## Test Coverage

### Generate Coverage Report

```bash
# Terminal report
PYTHONPATH=src pytest tests/ --cov=src --cov-report=term-missing

# HTML report (open htmlcov/index.html)
PYTHONPATH=src pytest tests/ --cov=src --cov-report=html
```

### Coverage Targets

| Module      | Target | Critical Paths             |
| ----------- | ------ | -------------------------- |
| `services/` | 85%    | All service classes        |
| `models/`   | 90%    | Data models, serialization |
| `utils/`    | 80%    | Cache, validators          |
| `app.py`    | 75%    | API routes                 |

---

## Testing Patterns Used

### 1. Arrange-Act-Assert (AAA)

```python
def test_example():
    # Arrange - set up test data
    validator = URLValidator()
    url = "example.com"

    # Act - perform the action
    result = validator.normalize(url)

    # Assert - verify the result
    assert result == "https://example.com"
```

### 2. Mocking External Services

```python
@patch('boto3.client')
def test_polly_synthesis(mock_boto):
    """Tests don't call real AWS = fast + free"""
    mock_polly = MagicMock()
    mock_boto.return_value = mock_polly
    mock_polly.synthesize_speech.return_value = {
        'AudioStream': io.BytesIO(b'fake audio')
    }
    # Test runs without AWS credentials
```

### 3. Fixtures for Shared Setup

```python
# conftest.py
@pytest.fixture
def mock_extractor():
    with patch('services.content_extractor.ContentExtractor') as mock:
        mock.return_value.extract.return_value = "Test content"
        yield mock

# test file
def test_something(mock_extractor):
    # mock_extractor is automatically injected
    pass
```

### 4. Parametrized Tests

```python
@pytest.mark.parametrize("url,expected", [
    ("example.com", "https://example.com"),
    ("HTTP://EXAMPLE.COM", "https://example.com"),
    ("https://example.com/", "https://example.com"),
])
def test_normalize_url(url, expected):
    assert normalize(url) == expected
```

### 5. Testing Edge Cases

```python
def test_empty_content():
    result = processor.process("")
    assert result.chunks == []

def test_very_long_content():
    content = "word " * 100000
    result = processor.process(content)
    assert len(result.chunks) > 1

def test_special_characters():
    result = extractor.extract("<p>Café résumé naïve</p>")
    assert "Café" in result
```

---

## Adding New Tests

### 1. Create Test Class

```python
# tests/test_new_feature.py
import pytest
from services.new_feature import NewFeature

class TestNewFeature:
    """Tests for NewFeature service."""

    def test_basic_functionality(self):
        feature = NewFeature()
        result = feature.do_something("input")
        assert result == "expected output"

    def test_error_handling(self):
        feature = NewFeature()
        with pytest.raises(ValueError):
            feature.do_something(None)
```

### 2. Use Fixtures

```python
@pytest.fixture
def feature():
    """Create a NewFeature instance for tests."""
    return NewFeature(config={"debug": True})

def test_with_fixture(feature):
    assert feature.do_something("input") == "expected"
```

### 3. Mock External Dependencies

```python
from unittest.mock import patch, MagicMock

def test_external_api():
    with patch('services.new_feature.requests.get') as mock_get:
        mock_get.return_value.json.return_value = {"data": "test"}
        feature = NewFeature()
        result = feature.fetch_data()
        assert result == {"data": "test"}
```

### 4. Run Your New Tests

```bash
# Run just your new test file
PYTHONPATH=src pytest tests/test_new_feature.py -v

# Run with coverage to ensure good coverage
PYTHONPATH=src pytest tests/test_new_feature.py --cov=src/services/new_feature
```

---

## Summary

These 136 tests ensure the AI Personal Tutor backend is:

- ✅ **Reliable** - All services are tested in isolation
- ✅ **Secure** - Script tags and XSS vectors are stripped
- ✅ **Fast** - Mocking prevents slow network/AWS calls
- ✅ **Maintainable** - Clear patterns make adding tests easy
- ✅ **Cost-effective** - No real AWS charges during testing

Run tests frequently during development:

```bash
# Quick validation
PYTHONPATH=src pytest tests/ -q

# Full verbose run
PYTHONPATH=src pytest tests/ -v --tb=short
```
