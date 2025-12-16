"""
Content Cache

Provides TTL-based caching for extracted content to avoid redundant
URL fetching and processing.

Features:
- In-memory cache with TTL support
- LRU eviction when capacity reached
- Thread-safe operations
- Cache statistics
- Optional persistence to file
"""

import json
import logging
import threading
import hashlib
from typing import Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import OrderedDict
import os

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached content entry."""
    key: str
    value: Dict
    created_at: datetime
    expires_at: datetime
    hits: int = 0
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'key': self.key,
            'value': self.value,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'hits': self.hits,
            'size_bytes': self.size_bytes
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'CacheEntry':
        """Create from dictionary."""
        return cls(
            key=data['key'],
            value=data['value'],
            created_at=datetime.fromisoformat(data['created_at']),
            expires_at=datetime.fromisoformat(data['expires_at']),
            hits=data.get('hits', 0),
            size_bytes=data.get('size_bytes', 0)
        )


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    current_size: int = 0
    max_size: int = 0
    entry_count: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate percentage."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0


class ContentCache:
    """
    TTL-based cache for content extraction results.

    Uses LRU eviction when capacity is reached.
    """

    def __init__(
        self,
        max_entries: int = 100,
        default_ttl_seconds: int = 3600,  # 1 hour
        max_size_bytes: int = 100 * 1024 * 1024,  # 100MB
        persistence_path: Optional[str] = None
    ):
        """
        Initialize the content cache.

        Args:
            max_entries: Maximum number of entries to cache
            default_ttl_seconds: Default time-to-live in seconds
            max_size_bytes: Maximum total cache size in bytes
            persistence_path: Optional file path for cache persistence
        """
        self.max_entries = max_entries
        self.default_ttl = timedelta(seconds=default_ttl_seconds)
        self.max_size_bytes = max_size_bytes
        self.persistence_path = persistence_path

        # Thread-safe ordered dict for LRU
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats(max_size=max_size_bytes)

        # Load persisted cache if available
        if persistence_path:
            self._load_from_file()

    def _generate_key(self, url: str) -> str:
        """Generate cache key from URL."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def _estimate_size(self, value: Dict) -> int:
        """Estimate size of cached value in bytes."""
        try:
            return len(json.dumps(value).encode())
        except Exception:
            return 1024  # Default estimate

    def get(self, url: str) -> Optional[Dict]:
        """
        Get cached content for URL.

        Args:
            url: URL to look up

        Returns:
            Cached content or None if not found/expired
        """
        key = self._generate_key(url)

        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                return None

            # Check expiration
            if entry.is_expired():
                self._remove_entry(key)
                self._stats.misses += 1
                logger.debug(f"Cache expired for URL: {url}")
                return None

            # Update access order (move to end for LRU)
            self._cache.move_to_end(key)
            entry.hits += 1
            self._stats.hits += 1

            logger.debug(f"Cache hit for URL: {url}")
            return entry.value

    def set(
        self,
        url: str,
        value: Dict,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Cache content for URL.

        Args:
            url: URL to cache
            value: Content to cache
            ttl_seconds: Optional custom TTL

        Returns:
            True if cached successfully
        """
        key = self._generate_key(url)
        ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else self.default_ttl

        size = self._estimate_size(value)
        now = datetime.utcnow()

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=now,
            expires_at=now + ttl,
            size_bytes=size
        )

        with self._lock:
            # Check if we need to evict entries
            while (
                len(self._cache) >= self.max_entries or
                self._stats.current_size + size > self.max_size_bytes
            ):
                if not self._evict_oldest():
                    # Can't evict anything, reject new entry
                    logger.warning("Cache full, cannot store entry")
                    return False

            # Remove existing entry if present
            if key in self._cache:
                self._remove_entry(key)

            # Add new entry
            self._cache[key] = entry
            self._stats.current_size += size
            self._stats.entry_count = len(self._cache)

            logger.debug(f"Cached content for URL: {url} (size: {size} bytes)")
            return True

    def _remove_entry(self, key: str) -> None:
        """Remove entry from cache (must hold lock)."""
        if key in self._cache:
            entry = self._cache.pop(key)
            self._stats.current_size -= entry.size_bytes
            self._stats.entry_count = len(self._cache)

    def _evict_oldest(self) -> bool:
        """
        Evict the oldest (LRU) entry.

        Returns:
            True if an entry was evicted
        """
        if not self._cache:
            return False

        # Get oldest entry (first in OrderedDict)
        oldest_key = next(iter(self._cache))
        self._remove_entry(oldest_key)
        self._stats.evictions += 1

        logger.debug(f"Evicted cache entry: {oldest_key}")
        return True

    def invalidate(self, url: str) -> bool:
        """
        Invalidate cached content for URL.

        Args:
            url: URL to invalidate

        Returns:
            True if entry was removed
        """
        key = self._generate_key(url)

        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                logger.debug(f"Invalidated cache for URL: {url}")
                return True
            return False

    def clear(self) -> int:
        """
        Clear all cached entries.

        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.current_size = 0
            self._stats.entry_count = 0

            logger.info(f"Cleared {count} cache entries")
            return count

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        removed = 0

        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]

            for key in expired_keys:
                self._remove_entry(key)
                removed += 1

        if removed > 0:
            logger.debug(f"Cleaned up {removed} expired cache entries")

        return removed

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                current_size=self._stats.current_size,
                max_size=self._stats.max_size,
                entry_count=self._stats.entry_count
            )

    def contains(self, url: str) -> bool:
        """Check if URL is cached (and not expired)."""
        key = self._generate_key(url)

        with self._lock:
            entry = self._cache.get(key)
            return entry is not None and not entry.is_expired()

    def _save_to_file(self) -> None:
        """Persist cache to file."""
        if not self.persistence_path:
            return

        try:
            with self._lock:
                data = {
                    'entries': [
                        entry.to_dict() for entry in self._cache.values()
                        if not entry.is_expired()
                    ],
                    'saved_at': datetime.utcnow().isoformat()
                }

            with open(self.persistence_path, 'w') as f:
                json.dump(data, f)

            logger.debug(f"Saved cache to {self.persistence_path}")

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def _load_from_file(self) -> None:
        """Load cache from file."""
        if not self.persistence_path or not os.path.exists(self.persistence_path):
            return

        try:
            with open(self.persistence_path, 'r') as f:
                data = json.load(f)

            entries = data.get('entries', [])
            loaded = 0

            with self._lock:
                for entry_data in entries:
                    entry = CacheEntry.from_dict(entry_data)

                    # Skip expired entries
                    if entry.is_expired():
                        continue

                    self._cache[entry.key] = entry
                    self._stats.current_size += entry.size_bytes
                    loaded += 1

                self._stats.entry_count = len(self._cache)

            logger.info(f"Loaded {loaded} cache entries from {self.persistence_path}")

        except Exception as e:
            logger.error(f"Failed to load cache: {e}")

    def persist(self) -> None:
        """Manually persist cache to file."""
        self._save_to_file()

    def __len__(self) -> int:
        """Get number of cached entries."""
        return len(self._cache)

    def __contains__(self, url: str) -> bool:
        """Check if URL is cached."""
        return self.contains(url)


# Global cache instance
_global_cache: Optional[ContentCache] = None


def get_cache(
    max_entries: int = 100,
    default_ttl_seconds: int = 3600
) -> ContentCache:
    """
    Get or create global cache instance.

    Args:
        max_entries: Maximum entries (used only on first call)
        default_ttl_seconds: Default TTL (used only on first call)

    Returns:
        Global ContentCache instance
    """
    global _global_cache

    if _global_cache is None:
        _global_cache = ContentCache(
            max_entries=max_entries,
            default_ttl_seconds=default_ttl_seconds
        )

    return _global_cache


# =============================================================================
# Demo/Testing
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    cache = ContentCache(max_entries=5, default_ttl_seconds=10)

    # Test basic operations
    print("Testing cache operations...")

    # Set some entries
    for i in range(3):
        url = f"https://example.com/page{i}"
        content = {'text': f'Content for page {i}', 'title': f'Page {i}'}
        cache.set(url, content)

    # Get entries
    for i in range(3):
        url = f"https://example.com/page{i}"
        result = cache.get(url)
        print(f"  {url}: {result['title'] if result else 'Not found'}")

    # Test cache miss
    result = cache.get("https://example.com/nonexistent")
    print(f"  Nonexistent URL: {result}")

    # Print stats
    stats = cache.get_stats()
    print(f"\nCache Stats:")
    print(f"  Hits: {stats.hits}")
    print(f"  Misses: {stats.misses}")
    print(f"  Hit Rate: {stats.hit_rate:.1f}%")
    print(f"  Entries: {stats.entry_count}")
    print(f"  Size: {stats.current_size} bytes")

    # Test eviction
    print("\nTesting eviction (max_entries=5)...")
    for i in range(10):
        url = f"https://example.com/new{i}"
        cache.set(url, {'text': f'New content {i}'})

    stats = cache.get_stats()
    print(f"  Entries after overflow: {stats.entry_count}")
    print(f"  Evictions: {stats.evictions}")
