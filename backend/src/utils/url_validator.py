"""
URL Validation Utilities

Provides comprehensive URL validation, accessibility checking,
redirect handling, and content type detection.

Features:
- URL format validation
- Domain blacklist/whitelist support
- Accessibility checking with retry logic
- Redirect chain following
- Content type detection
- Rate limiting awareness
"""

import re
import logging
from typing import Dict, Optional, Tuple, List
from urllib.parse import urlparse, urljoin
from dataclasses import dataclass
from enum import Enum
import time

import requests

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Supported content types."""
    HTML = "html"
    PDF = "pdf"
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    XML = "xml"
    UNSUPPORTED = "unsupported"


@dataclass
class URLValidationResult:
    """Result of URL validation."""
    is_valid: bool
    url: str
    final_url: str  # After redirects
    content_type: ContentType
    content_length: Optional[int]
    status_code: Optional[int]
    redirect_chain: List[str]
    error: Optional[str]
    response_time_ms: int


class URLValidator:
    """
    Validates and checks accessibility of URLs.
    """

    # Regex for basic URL validation
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )

    # Content type mappings
    CONTENT_TYPE_MAP = {
        'text/html': ContentType.HTML,
        'application/xhtml+xml': ContentType.HTML,
        'application/pdf': ContentType.PDF,
        'text/plain': ContentType.TEXT,
        'text/markdown': ContentType.MARKDOWN,
        'application/json': ContentType.JSON,
        'application/xml': ContentType.XML,
        'text/xml': ContentType.XML,
    }

    # Default blocked domains (can be extended)
    DEFAULT_BLOCKED_DOMAINS = {
        'localhost',
        '127.0.0.1',
        '0.0.0.0',
        '192.168.',
        '10.',
        '172.16.',
    }

    # User agent
    USER_AGENT = (
        "Mozilla/5.0 (compatible; AITutorBot/1.0; "
        "+https://github.com/aico-delta)"
    )

    def __init__(
        self,
        timeout: int = 15,
        max_redirects: int = 5,
        max_content_size: int = 50 * 1024 * 1024,  # 50MB
        blocked_domains: Optional[set] = None,
        allowed_domains: Optional[set] = None,
        allow_private: bool = False
    ):
        """
        Initialize the URL validator.

        Args:
            timeout: Request timeout in seconds
            max_redirects: Maximum number of redirects to follow
            max_content_size: Maximum content size to accept (bytes)
            blocked_domains: Additional domains to block
            allowed_domains: If set, only these domains are allowed
            allow_private: Allow private/local IP addresses
        """
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.max_content_size = max_content_size
        self.allow_private = allow_private

        # Set up domain filters
        self.blocked_domains = blocked_domains or set()
        if not allow_private:
            self.blocked_domains.update(self.DEFAULT_BLOCKED_DOMAINS)

        self.allowed_domains = allowed_domains

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        self.session.max_redirects = max_redirects

    def validate(self, url: str) -> URLValidationResult:
        """
        Validate a URL and check its accessibility.

        Args:
            url: URL to validate

        Returns:
            URLValidationResult with validation details
        """
        start_time = time.time()
        redirect_chain = []

        # Basic format validation
        if not self._is_valid_format(url):
            return URLValidationResult(
                is_valid=False,
                url=url,
                final_url=url,
                content_type=ContentType.UNSUPPORTED,
                content_length=None,
                status_code=None,
                redirect_chain=[],
                error="Invalid URL format",
                response_time_ms=0
            )

        # Parse URL
        parsed = urlparse(url)

        # Check domain restrictions
        domain_error = self._check_domain(parsed.netloc)
        if domain_error:
            return URLValidationResult(
                is_valid=False,
                url=url,
                final_url=url,
                content_type=ContentType.UNSUPPORTED,
                content_length=None,
                status_code=None,
                redirect_chain=[],
                error=domain_error,
                response_time_ms=0
            )

        # Check accessibility with HEAD request first
        try:
            response = self.session.head(
                url,
                timeout=self.timeout,
                allow_redirects=True
            )

            # Track redirects
            if response.history:
                redirect_chain = [r.url for r in response.history]

            final_url = response.url
            status_code = response.status_code

            # Check status code
            if status_code >= 400:
                return URLValidationResult(
                    is_valid=False,
                    url=url,
                    final_url=final_url,
                    content_type=ContentType.UNSUPPORTED,
                    content_length=None,
                    status_code=status_code,
                    redirect_chain=redirect_chain,
                    error=f"HTTP {status_code} error",
                    response_time_ms=int((time.time() - start_time) * 1000)
                )

            # Get content info
            content_type = self._detect_content_type(response.headers)
            content_length = self._get_content_length(response.headers)

            # Check content size
            if content_length and content_length > self.max_content_size:
                return URLValidationResult(
                    is_valid=False,
                    url=url,
                    final_url=final_url,
                    content_type=content_type,
                    content_length=content_length,
                    status_code=status_code,
                    redirect_chain=redirect_chain,
                    error=f"Content too large: {content_length} bytes",
                    response_time_ms=int((time.time() - start_time) * 1000)
                )

            # Check if content type is supported
            if content_type == ContentType.UNSUPPORTED:
                return URLValidationResult(
                    is_valid=False,
                    url=url,
                    final_url=final_url,
                    content_type=content_type,
                    content_length=content_length,
                    status_code=status_code,
                    redirect_chain=redirect_chain,
                    error="Unsupported content type",
                    response_time_ms=int((time.time() - start_time) * 1000)
                )

            # All checks passed
            return URLValidationResult(
                is_valid=True,
                url=url,
                final_url=final_url,
                content_type=content_type,
                content_length=content_length,
                status_code=status_code,
                redirect_chain=redirect_chain,
                error=None,
                response_time_ms=int((time.time() - start_time) * 1000)
            )

        except requests.exceptions.TooManyRedirects:
            return URLValidationResult(
                is_valid=False,
                url=url,
                final_url=url,
                content_type=ContentType.UNSUPPORTED,
                content_length=None,
                status_code=None,
                redirect_chain=redirect_chain,
                error="Too many redirects",
                response_time_ms=int((time.time() - start_time) * 1000)
            )

        except requests.exceptions.SSLError:
            return URLValidationResult(
                is_valid=False,
                url=url,
                final_url=url,
                content_type=ContentType.UNSUPPORTED,
                content_length=None,
                status_code=None,
                redirect_chain=[],
                error="SSL certificate error",
                response_time_ms=int((time.time() - start_time) * 1000)
            )

        except requests.exceptions.ConnectionError:
            return URLValidationResult(
                is_valid=False,
                url=url,
                final_url=url,
                content_type=ContentType.UNSUPPORTED,
                content_length=None,
                status_code=None,
                redirect_chain=[],
                error="Connection failed",
                response_time_ms=int((time.time() - start_time) * 1000)
            )

        except requests.exceptions.Timeout:
            return URLValidationResult(
                is_valid=False,
                url=url,
                final_url=url,
                content_type=ContentType.UNSUPPORTED,
                content_length=None,
                status_code=None,
                redirect_chain=[],
                error=f"Request timed out after {self.timeout}s",
                response_time_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            logger.exception(f"Unexpected error validating URL: {url}")
            return URLValidationResult(
                is_valid=False,
                url=url,
                final_url=url,
                content_type=ContentType.UNSUPPORTED,
                content_length=None,
                status_code=None,
                redirect_chain=[],
                error=f"Unexpected error: {str(e)}",
                response_time_ms=int((time.time() - start_time) * 1000)
            )

    def _is_valid_format(self, url: str) -> bool:
        """Check if URL has valid format."""
        return bool(self.URL_PATTERN.match(url))

    def _check_domain(self, domain: str) -> Optional[str]:
        """
        Check domain against allow/block lists.

        Returns error message or None if allowed.
        """
        domain_lower = domain.lower()

        # Check allowed domains first (whitelist)
        if self.allowed_domains:
            if not any(
                domain_lower == d or domain_lower.endswith(f'.{d}')
                for d in self.allowed_domains
            ):
                return f"Domain not in allowed list: {domain}"

        # Check blocked domains
        for blocked in self.blocked_domains:
            if blocked in domain_lower:
                return f"Domain is blocked: {domain}"

        return None

    def _detect_content_type(self, headers: Dict) -> ContentType:
        """Detect content type from headers."""
        content_type = headers.get('content-type', '').lower()

        for mime_type, ct in self.CONTENT_TYPE_MAP.items():
            if mime_type in content_type:
                return ct

        return ContentType.UNSUPPORTED

    def _get_content_length(self, headers: Dict) -> Optional[int]:
        """Get content length from headers."""
        try:
            return int(headers.get('content-length', 0))
        except (ValueError, TypeError):
            return None

    def normalize_url(self, url: str, base_url: Optional[str] = None) -> str:
        """
        Normalize a URL, handling relative URLs if base provided.

        Args:
            url: URL to normalize
            base_url: Optional base URL for relative URLs

        Returns:
            Normalized absolute URL
        """
        # Strip whitespace
        url = url.strip()

        # Handle relative URLs
        if base_url and not url.startswith(('http://', 'https://')):
            url = urljoin(base_url, url)

        # Add https if no scheme
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Remove trailing slash from path (except root)
        parsed = urlparse(url)
        if parsed.path and parsed.path != '/' and parsed.path.endswith('/'):
            url = url.rstrip('/')

        return url

    def is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs are from the same domain."""
        try:
            domain1 = urlparse(url1).netloc.lower()
            domain2 = urlparse(url2).netloc.lower()
            return domain1 == domain2
        except Exception:
            return False

    def extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return ""


class RateLimiter:
    """
    Simple rate limiter for URL requests per domain.
    """

    def __init__(self, requests_per_second: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second per domain
        """
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request: Dict[str, float] = {}

    def wait(self, domain: str) -> float:
        """
        Wait if necessary to respect rate limit.

        Args:
            domain: Domain being requested

        Returns:
            Time waited in seconds
        """
        now = time.time()
        last = self.last_request.get(domain, 0)
        elapsed = now - last

        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            time.sleep(wait_time)
            self.last_request[domain] = time.time()
            return wait_time

        self.last_request[domain] = now
        return 0.0

    def can_request(self, domain: str) -> bool:
        """Check if a request can be made without waiting."""
        now = time.time()
        last = self.last_request.get(domain, 0)
        return (now - last) >= self.min_interval


# =============================================================================
# Demo/Testing
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    validator = URLValidator()

    # Test URLs
    test_urls = [
        "https://docs.python.org/3/tutorial/classes.html",
        "https://example.com",
        "invalid-url",
        "https://httpstat.us/404",
        "https://httpstat.us/200",
    ]

    for url in test_urls:
        print(f"\nValidating: {url}")
        print("-" * 50)

        result = validator.validate(url)

        print(f"  Valid: {result.is_valid}")
        print(f"  Final URL: {result.final_url}")
        print(f"  Content Type: {result.content_type.value}")
        print(f"  Status Code: {result.status_code}")
        print(f"  Response Time: {result.response_time_ms}ms")

        if result.redirect_chain:
            print(f"  Redirects: {len(result.redirect_chain)}")

        if result.error:
            print(f"  Error: {result.error}")
