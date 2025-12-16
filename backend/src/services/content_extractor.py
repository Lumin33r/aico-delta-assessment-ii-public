"""
Content Extractor Service

Extracts clean, readable text content from URLs using trafilatura
with BeautifulSoup as fallback.

Features:
- Main content extraction (removes navigation, ads, etc.)
- Metadata extraction (title, author, date)
- Multiple extraction strategies for reliability
- Content cleaning and normalization
"""

import re
import logging
from typing import Dict, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# Optional: trafilatura for better extraction
try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    logging.warning("trafilatura not installed - using BeautifulSoup fallback")

logger = logging.getLogger(__name__)


class ContentExtractor:
    """
    Extracts readable content from web pages.
    """

    # User agent for requests
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # Tags to remove during BeautifulSoup extraction
    REMOVE_TAGS = [
        'script', 'style', 'nav', 'header', 'footer',
        'aside', 'form', 'iframe', 'noscript', 'svg',
        'button', 'input', 'select', 'textarea'
    ]

    # Classes/IDs that typically contain navigation or ads
    REMOVE_PATTERNS = [
        r'nav', r'menu', r'sidebar', r'footer', r'header',
        r'comment', r'share', r'social', r'related', r'recommend',
        r'advertis', r'sponsor', r'promo', r'banner', r'cookie'
    ]

    def __init__(self, timeout: int = 30, max_content_length: int = 100000):
        """
        Initialize the content extractor.

        Args:
            timeout: Request timeout in seconds
            max_content_length: Maximum content length to return
        """
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

    def extract(self, url: str) -> Dict:
        """
        Extract content from a URL.

        Args:
            url: URL to extract content from

        Returns:
            Dict with text, title, url, metadata
        """
        logger.info(f"Extracting content from: {url}")

        # Fetch the page
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            html = response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch URL: {e}")
            raise ValueError(f"Could not fetch URL: {str(e)}")

        # Try trafilatura first (if available)
        if TRAFILATURA_AVAILABLE:
            result = self._extract_with_trafilatura(html, url)
            if result and result.get('text'):
                return result

        # Fall back to BeautifulSoup
        result = self._extract_with_beautifulsoup(html, url)

        if not result.get('text'):
            raise ValueError("Could not extract meaningful content from URL")

        return result

    def _extract_with_trafilatura(self, html: str, url: str) -> Optional[Dict]:
        """
        Extract content using trafilatura.

        Args:
            html: Raw HTML content
            url: Source URL

        Returns:
            Extraction result or None
        """
        try:
            # Extract main content
            text = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_precision=True,
                url=url
            )

            if not text:
                return None

            # Extract metadata
            metadata = trafilatura.extract_metadata(html)

            title = ""
            author = ""
            date = ""
            description = ""

            if metadata:
                title = metadata.title or ""
                author = metadata.author or ""
                date = metadata.date or ""
                description = metadata.description or ""

            # Clean and normalize text
            text = self._clean_text(text)

            return {
                'text': text[:self.max_content_length],
                'title': title,
                'url': url,
                'domain': urlparse(url).netloc,
                'metadata': {
                    'author': author,
                    'date': date,
                    'description': description,
                    'word_count': len(text.split()),
                    'extraction_method': 'trafilatura'
                }
            }

        except Exception as e:
            logger.warning(f"Trafilatura extraction failed: {e}")
            return None

    def _extract_with_beautifulsoup(self, html: str, url: str) -> Dict:
        """
        Extract content using BeautifulSoup.

        Args:
            html: Raw HTML content
            url: Source URL

        Returns:
            Extraction result
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Extract title
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Try to find og:title or h1
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content', '')

        if not title:
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)

        # Extract description
        description = ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content', '')

        # Remove unwanted elements
        for tag_name in self.REMOVE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Remove elements with navigation-like classes/ids
        for pattern in self.REMOVE_PATTERNS:
            regex = re.compile(pattern, re.IGNORECASE)
            for tag in soup.find_all(class_=regex):
                tag.decompose()
            for tag in soup.find_all(id=regex):
                tag.decompose()

        # Try to find main content area
        main_content = None

        # Look for common main content containers
        content_selectors = [
            'article',
            'main',
            '[role="main"]',
            '.post-content',
            '.article-content',
            '.entry-content',
            '.content',
            '#content',
            '.post',
            '.article'
        ]

        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break

        # Fall back to body
        if not main_content:
            main_content = soup.find('body') or soup

        # Extract text
        text = main_content.get_text(separator='\n', strip=True)
        text = self._clean_text(text)

        return {
            'text': text[:self.max_content_length],
            'title': title,
            'url': url,
            'domain': urlparse(url).netloc,
            'metadata': {
                'description': description,
                'word_count': len(text.split()),
                'extraction_method': 'beautifulsoup'
            }
        }

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove lines that are likely navigation/menu items
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()

            # Skip very short lines (likely menu items)
            if len(line) < 20 and '|' in line:
                continue

            # Skip lines that are just punctuation
            if len(line) < 5 and not any(c.isalnum() for c in line):
                continue

            cleaned_lines.append(line)

        text = '\n'.join(cleaned_lines)

        # Final cleanup
        text = text.strip()

        return text

    def extract_links(self, url: str) -> list:
        """
        Extract all links from a page (for future crawling).

        Args:
            url: URL to extract links from

        Returns:
            List of absolute URLs
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            links = set()

            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']

                # Skip anchors and javascript
                if href.startswith('#') or href.startswith('javascript:'):
                    continue

                # Make absolute
                if href.startswith('/'):
                    href = base_url + href
                elif not href.startswith('http'):
                    continue

                links.add(href)

            return list(links)

        except Exception as e:
            logger.error(f"Failed to extract links: {e}")
            return []


# =============================================================================
# Demo/Testing
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    extractor = ContentExtractor()

    # Test URL
    test_url = "https://docs.python.org/3/tutorial/classes.html"

    print(f"Extracting content from: {test_url}")
    print("-" * 50)

    try:
        result = extractor.extract(test_url)

        print(f"Title: {result['title']}")
        print(f"Domain: {result['domain']}")
        print(f"Word count: {result['metadata']['word_count']}")
        print(f"Method: {result['metadata']['extraction_method']}")
        print(f"\nFirst 500 chars:")
        print(result['text'][:500])

    except Exception as e:
        print(f"Error: {e}")
