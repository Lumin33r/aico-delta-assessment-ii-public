# Backend Tests

This directory contains unit and integration tests for the AI Personal Tutor backend.

## Running Tests

```bash
# From backend directory
cd backend

# Activate virtual environment
source venv/bin/activate

# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_content_extraction.py -v

# Run specific test class
pytest tests/test_content_extraction.py::TestContentExtractor -v

# Run specific test
pytest tests/test_content_extraction.py::TestContentExtractor::test_extract_success -v
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_content_extraction.py   # Content extraction tests
├── test_podcast_generator.py    # Podcast generation tests
└── test_audio_synthesizer.py    # Audio synthesis tests
```

## Test Coverage

Target: 80% code coverage

Key areas to test:

- URL validation and normalization
- Content extraction from various HTML structures
- Content processing and chunking
- Cache operations and eviction
- Podcast script generation
- Audio synthesis
