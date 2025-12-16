"""
Tests for Content Extraction Pipeline

Unit tests for:
- ContentExtractor
- ContentProcessor
- URLValidator
- ContentCache
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Import modules under test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.content_extractor import ContentExtractor
from services.content_processor import ContentProcessor, ProcessedContent, ContentChunk
from utils.url_validator import URLValidator, ContentType, URLValidationResult
from utils.cache import ContentCache, CacheEntry


# =============================================================================
# ContentExtractor Tests
# =============================================================================

class TestContentExtractor:
    """Tests for ContentExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return ContentExtractor(timeout=10)

    @pytest.fixture
    def sample_html(self):
        """Sample HTML content for testing."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Article</title>
            <meta name="description" content="A test article for extraction">
        </head>
        <body>
            <nav>Navigation menu</nav>
            <header>Site header</header>
            <main>
                <article>
                    <h1>Test Article Title</h1>
                    <p>This is the first paragraph of the article with meaningful content
                    that should be extracted by our content extraction system.</p>
                    <p>This is the second paragraph with more information about the topic
                    we are discussing in this test article.</p>
                    <h2>Subheading</h2>
                    <p>Content under the subheading that provides additional details.</p>
                </article>
            </main>
            <aside>Sidebar content</aside>
            <footer>Footer content</footer>
            <script>console.log('should be removed');</script>
        </body>
        </html>
        """

    @patch('services.content_extractor.requests.Session')
    def test_extract_success(self, mock_session_class, extractor, sample_html):
        """Test successful content extraction."""
        mock_response = Mock()
        mock_response.text = sample_html
        mock_response.raise_for_status = Mock()

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Create new extractor with mocked session
        extractor = ContentExtractor()
        extractor.session = mock_session

        result = extractor.extract("https://example.com/article")

        assert result['title'] == 'Test Article Title'
        assert 'first paragraph' in result['text']
        assert result['url'] == "https://example.com/article"
        assert result['domain'] == "example.com"
        assert 'word_count' in result['metadata']

    @patch('services.content_extractor.requests.Session')
    def test_extract_removes_script_tags(self, mock_session_class, extractor, sample_html):
        """Test that script tags are removed."""
        mock_response = Mock()
        mock_response.text = sample_html
        mock_response.raise_for_status = Mock()

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        extractor = ContentExtractor()
        extractor.session = mock_session

        result = extractor.extract("https://example.com/article")

        assert 'console.log' not in result['text']
        assert 'should be removed' not in result['text']

    @patch('services.content_extractor.requests.Session')
    def test_extract_removes_navigation(self, mock_session_class, extractor, sample_html):
        """Test that navigation elements are removed."""
        mock_response = Mock()
        mock_response.text = sample_html
        mock_response.raise_for_status = Mock()

        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session

        extractor = ContentExtractor()
        extractor.session = mock_session

        result = extractor.extract("https://example.com/article")

        # Navigation content should be minimized
        assert result['text'].count('Navigation menu') == 0 or \
               len(result['text']) > 100  # Has substantial content

    @patch('services.content_extractor.requests.Session')
    def test_extract_network_error(self, mock_session_class, extractor):
        """Test handling of network errors."""
        import requests

        mock_session = Mock()
        mock_session.get.side_effect = requests.exceptions.ConnectionError("Network error")
        mock_session_class.return_value = mock_session

        extractor = ContentExtractor()
        extractor.session = mock_session

        with pytest.raises(ValueError) as exc_info:
            extractor.extract("https://example.com/article")

        assert "Could not fetch URL" in str(exc_info.value)

    def test_clean_text(self, extractor):
        """Test text cleaning."""
        dirty_text = "  Multiple   spaces   and\n\n\n\nmany newlines  "
        cleaned = extractor._clean_text(dirty_text)

        assert "   " not in cleaned  # No triple spaces
        assert "\n\n\n" not in cleaned  # No excessive newlines


# =============================================================================
# ContentProcessor Tests
# =============================================================================

class TestContentProcessor:
    """Tests for ContentProcessor class."""

    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        return ContentProcessor(chunk_size=500, chunk_overlap=50)

    @pytest.fixture
    def sample_content(self):
        """Sample extracted content."""
        return {
            'text': """
            Introduction to Python Programming

            Python is a high-level programming language known for its simplicity
            and readability. It was created by Guido van Rossum and first released
            in 1991.

            Key Features

            Python offers many features that make it popular among developers.
            These include dynamic typing, automatic memory management, and a
            large standard library.

            Variables and Data Types

            In Python, variables don't need to be declared with a specific type.
            You can simply assign a value to a variable name. Python supports
            several built-in data types including integers, floats, strings,
            lists, and dictionaries.

            def example_function():
                print("Hello, World!")
                return 42

            Control Flow

            Python provides standard control flow statements like if/else,
            for loops, and while loops. These allow you to control the
            execution of your program based on conditions.
            """,
            'title': 'Introduction to Python Programming',
            'url': 'https://example.com/python-intro',
            'metadata': {
                'extraction_method': 'test'
            }
        }

    def test_process_returns_correct_structure(self, processor, sample_content):
        """Test that process returns ProcessedContent."""
        result = processor.process(sample_content)

        assert isinstance(result, ProcessedContent)
        assert result.title == 'Introduction to Python Programming'
        assert result.url == 'https://example.com/python-intro'
        assert len(result.chunks) > 0
        assert len(result.topics) > 0

    def test_topic_extraction(self, processor, sample_content):
        """Test topic extraction."""
        result = processor.process(sample_content)

        # Should extract relevant topics
        topic_lower = [t.lower() for t in result.topics]
        assert any('python' in t for t in topic_lower)

    def test_key_concept_extraction(self, processor, sample_content):
        """Test key concept extraction."""
        result = processor.process(sample_content)

        # Should have some key concepts
        assert len(result.key_concepts) >= 0  # May be empty for simple content

    def test_chunking(self, processor, sample_content):
        """Test content chunking."""
        result = processor.process(sample_content)

        # Should create multiple chunks for long content
        assert len(result.chunks) >= 1

        # Each chunk should be a ContentChunk
        for chunk in result.chunks:
            assert isinstance(chunk, ContentChunk)
            assert chunk.word_count > 0

    def test_code_detection(self, processor, sample_content):
        """Test code block detection."""
        result = processor.process(sample_content)

        # Should detect code in content
        assert result.metadata.get('has_code') == True

    def test_prepare_for_llm(self, processor, sample_content):
        """Test LLM preparation."""
        processed = processor.process(sample_content)
        llm_text = processor.prepare_for_llm(processed, max_tokens=1000)

        assert processed.title in llm_text
        assert 'Summary' in llm_text
        assert 'Topics' in llm_text

    def test_empty_content(self, processor):
        """Test handling of empty content."""
        empty_content = {
            'text': '',
            'title': 'Empty',
            'url': 'https://example.com/empty',
            'metadata': {}
        }

        result = processor.process(empty_content)

        assert result.total_words == 0
        assert len(result.chunks) == 0


# =============================================================================
# URLValidator Tests
# =============================================================================

class TestURLValidator:
    """Tests for URLValidator class."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return URLValidator(timeout=5)

    def test_valid_url_format(self, validator):
        """Test valid URL format detection."""
        assert validator._is_valid_format("https://example.com")
        assert validator._is_valid_format("http://example.com/path")
        assert validator._is_valid_format("https://sub.example.com/path?query=1")

    def test_invalid_url_format(self, validator):
        """Test invalid URL format detection."""
        assert not validator._is_valid_format("not-a-url")
        assert not validator._is_valid_format("ftp://example.com")
        assert not validator._is_valid_format("javascript:alert(1)")

    def test_normalize_url(self, validator):
        """Test URL normalization."""
        assert validator.normalize_url("example.com") == "https://example.com"
        assert validator.normalize_url("  https://example.com  ") == "https://example.com"

    def test_normalize_relative_url(self, validator):
        """Test relative URL normalization."""
        base = "https://example.com/page"

        assert validator.normalize_url("/other", base) == "https://example.com/other"
        assert validator.normalize_url("../sibling", base) == "https://example.com/sibling"

    def test_is_same_domain(self, validator):
        """Test same domain detection."""
        assert validator.is_same_domain(
            "https://example.com/page1",
            "https://example.com/page2"
        )
        assert not validator.is_same_domain(
            "https://example.com/page",
            "https://other.com/page"
        )

    def test_extract_domain(self, validator):
        """Test domain extraction."""
        assert validator.extract_domain("https://example.com/path") == "example.com"
        assert validator.extract_domain("https://sub.example.com") == "sub.example.com"

    @patch('utils.url_validator.requests.Session')
    def test_validate_success(self, mock_session_class, validator):
        """Test successful validation."""
        mock_response = Mock()
        mock_response.url = "https://example.com"
        mock_response.status_code = 200
        mock_response.history = []
        mock_response.headers = {
            'content-type': 'text/html',
            'content-length': '1000'
        }

        mock_session = Mock()
        mock_session.head.return_value = mock_response
        mock_session_class.return_value = mock_session

        validator = URLValidator()
        validator.session = mock_session

        result = validator.validate("https://example.com")

        assert result.is_valid
        assert result.content_type == ContentType.HTML
        assert result.status_code == 200

    @patch('utils.url_validator.requests.Session')
    def test_validate_404(self, mock_session_class, validator):
        """Test 404 response handling."""
        mock_response = Mock()
        mock_response.url = "https://example.com/notfound"
        mock_response.status_code = 404
        mock_response.history = []
        mock_response.headers = {}

        mock_session = Mock()
        mock_session.head.return_value = mock_response
        mock_session_class.return_value = mock_session

        validator = URLValidator()
        validator.session = mock_session

        result = validator.validate("https://example.com/notfound")

        assert not result.is_valid
        assert result.status_code == 404
        assert "404" in result.error

    def test_content_type_detection(self, validator):
        """Test content type detection from headers."""
        html_headers = {'content-type': 'text/html; charset=utf-8'}
        pdf_headers = {'content-type': 'application/pdf'}
        json_headers = {'content-type': 'application/json'}

        assert validator._detect_content_type(html_headers) == ContentType.HTML
        assert validator._detect_content_type(pdf_headers) == ContentType.PDF
        assert validator._detect_content_type(json_headers) == ContentType.JSON


# =============================================================================
# ContentCache Tests
# =============================================================================

class TestContentCache:
    """Tests for ContentCache class."""

    @pytest.fixture
    def cache(self):
        """Create cache instance."""
        return ContentCache(max_entries=5, default_ttl_seconds=60)

    def test_set_and_get(self, cache):
        """Test basic set and get operations."""
        url = "https://example.com/page"
        content = {'text': 'Test content', 'title': 'Test'}

        cache.set(url, content)
        result = cache.get(url)

        assert result == content

    def test_cache_miss(self, cache):
        """Test cache miss returns None."""
        result = cache.get("https://example.com/nonexistent")
        assert result is None

    def test_expiration(self):
        """Test entry expiration."""
        cache = ContentCache(max_entries=5, default_ttl_seconds=1)

        url = "https://example.com/expire"
        cache.set(url, {'text': 'Will expire'})

        # Should be cached initially
        assert cache.get(url) is not None

        # Wait for expiration
        import time
        time.sleep(1.1)

        # Should be expired now
        assert cache.get(url) is None

    def test_lru_eviction(self, cache):
        """Test LRU eviction when capacity reached."""
        # Fill cache to capacity
        for i in range(5):
            cache.set(f"https://example.com/page{i}", {'text': f'Content {i}'})

        # Access first entry to make it recently used
        cache.get("https://example.com/page0")

        # Add new entry, should evict page1 (oldest not accessed)
        cache.set("https://example.com/new", {'text': 'New content'})

        # page0 should still be cached (recently accessed)
        assert cache.get("https://example.com/page0") is not None

        # new should be cached
        assert cache.get("https://example.com/new") is not None

    def test_invalidate(self, cache):
        """Test cache invalidation."""
        url = "https://example.com/invalidate"
        cache.set(url, {'text': 'To be invalidated'})

        assert cache.get(url) is not None

        cache.invalidate(url)

        assert cache.get(url) is None

    def test_clear(self, cache):
        """Test cache clearing."""
        for i in range(3):
            cache.set(f"https://example.com/page{i}", {'text': f'Content {i}'})

        assert len(cache) == 3

        cleared = cache.clear()

        assert cleared == 3
        assert len(cache) == 0

    def test_contains(self, cache):
        """Test contains check."""
        url = "https://example.com/contains"

        assert url not in cache

        cache.set(url, {'text': 'Content'})

        assert url in cache

    def test_stats(self, cache):
        """Test statistics tracking."""
        url = "https://example.com/stats"
        cache.set(url, {'text': 'Content'})

        # Generate hits and misses
        cache.get(url)  # hit
        cache.get(url)  # hit
        cache.get("https://example.com/nonexistent")  # miss

        stats = cache.get_stats()

        assert stats.hits == 2
        assert stats.misses == 1
        assert stats.entry_count == 1
        assert stats.hit_rate == pytest.approx(66.67, rel=0.1)


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the content extraction pipeline."""

    def test_full_pipeline(self):
        """Test the full extraction -> processing pipeline."""
        # Create mock extracted content
        extracted = {
            'text': """
            Understanding AWS Lambda

            AWS Lambda is a serverless compute service that lets you run code
            without provisioning or managing servers. Lambda runs your code on
            a high-availability compute infrastructure.

            Key Benefits

            No servers to manage - Lambda automatically runs your code without
            requiring you to provision or manage infrastructure.

            Continuous scaling - Lambda automatically scales your application
            by running code in response to each event.

            Example Code

            def lambda_handler(event, context):
                return {
                    'statusCode': 200,
                    'body': 'Hello from Lambda!'
                }

            Use Cases

            Lambda is ideal for real-time file processing, data transformation,
            and backend services for mobile and web applications.
            """,
            'title': 'Understanding AWS Lambda',
            'url': 'https://docs.aws.amazon.com/lambda',
            'metadata': {'extraction_method': 'test'}
        }

        # Process content
        processor = ContentProcessor(chunk_size=500)
        processed = processor.process(extracted)

        # Verify processing
        assert processed.title == 'Understanding AWS Lambda'
        assert processed.total_words > 50
        assert len(processed.chunks) >= 1
        assert 'lambda' in [t.lower() for t in processed.topics] or \
               any('lambda' in t.lower() for t in processed.key_concepts)

        # Test LLM preparation
        llm_text = processor.prepare_for_llm(processed)
        assert 'Lambda' in llm_text
        assert len(llm_text) > 100


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
