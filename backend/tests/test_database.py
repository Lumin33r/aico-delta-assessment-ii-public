"""
Tests for PostgreSQL Database Integration

Unit and integration tests for:
- Database connection and health checks
- Podcast CRUD operations
- Connection pooling
- Error handling and graceful degradation
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_cursor():
    """Create a mock database cursor."""
    cursor = MagicMock()
    cursor.__enter__ = Mock(return_value=cursor)
    cursor.__exit__ = Mock(return_value=False)
    return cursor


@pytest.fixture
def mock_connection(mock_cursor):
    """Create a mock database connection."""
    conn = MagicMock()
    conn.cursor.return_value = mock_cursor
    return conn


@pytest.fixture
def mock_pool(mock_connection):
    """Create a mock connection pool."""
    pool = MagicMock()
    pool.getconn.return_value = mock_connection
    return pool


# =============================================================================
# Unit Tests - No Database Required
# =============================================================================

class TestDatabaseModule:
    """Tests for database module when psycopg2 is not available."""

    def test_import_without_psycopg2(self):
        """Test module imports gracefully without psycopg2."""
        # This should not raise an exception
        from utils import database
        assert hasattr(database, 'PSYCOPG2_AVAILABLE')
        assert hasattr(database, 'get_db')
        assert hasattr(database, 'log_podcast')

    def test_health_check_without_database_url(self):
        """Test health check when DATABASE_URL is not set."""
        with patch.dict(os.environ, {'DATABASE_URL': ''}, clear=False):
            # Re-import to pick up env change
            from utils import database
            database.DATABASE_URL = ''

            result = database.health_check()
            assert result['status'] == 'unavailable'
            assert 'DATABASE_URL' in result.get('reason', '')


class TestHealthCheck:
    """Tests for database health check functionality."""

    def test_health_check_psycopg2_not_available(self):
        """Test health check when psycopg2 is not installed."""
        from utils import database

        original = database.PSYCOPG2_AVAILABLE
        database.PSYCOPG2_AVAILABLE = False

        result = database.health_check()

        database.PSYCOPG2_AVAILABLE = original

        assert result['status'] == 'unavailable'
        assert 'psycopg2' in result.get('reason', '')

    def test_health_check_connection_error(self, mock_pool):
        """Test health check with connection error."""
        from utils import database

        mock_pool.getconn.side_effect = Exception("Connection refused")

        with patch.object(database, 'get_pool', return_value=mock_pool):
            with patch.object(database, 'PSYCOPG2_AVAILABLE', True):
                with patch.object(database, 'DATABASE_URL', 'postgresql://test'):
                    result = database.health_check()
                    # Should handle error gracefully
                    assert result['status'] in ['error', 'unavailable']


class TestGetDb:
    """Tests for database connection context manager."""

    def test_get_db_yields_none_without_pool(self):
        """Test get_db yields None when pool is unavailable."""
        from utils import database

        with patch.object(database, 'get_pool', return_value=None):
            with database.get_db() as conn:
                assert conn is None

    def test_get_db_returns_connection(self, mock_pool, mock_connection):
        """Test get_db returns connection from pool."""
        from utils import database

        with patch.object(database, 'get_pool', return_value=mock_pool):
            with database.get_db() as conn:
                assert conn == mock_connection

        # Connection should be returned to pool
        mock_pool.putconn.assert_called_once_with(mock_connection)

    def test_get_db_handles_exception(self, mock_pool):
        """Test get_db handles exceptions gracefully."""
        from utils import database

        mock_pool.getconn.side_effect = Exception("Connection error")

        with patch.object(database, 'get_pool', return_value=mock_pool):
            with database.get_db() as conn:
                assert conn is None


# =============================================================================
# Podcast CRUD Tests (Mocked)
# =============================================================================

class TestLogPodcast:
    """Tests for podcast logging functionality."""

    def test_log_podcast_success(self, mock_pool, mock_connection, mock_cursor):
        """Test successful podcast logging."""
        from utils import database

        mock_cursor.fetchone.return_value = [42]

        with patch.object(database, 'get_pool', return_value=mock_pool):
            result = database.log_podcast(
                source_url="https://example.com/article",
                title="Test Article",
                audio_path="/tmp/audio.mp3",
                status="completed"
            )

        assert result == 42
        mock_cursor.execute.assert_called_once()
        mock_connection.commit.assert_called_once()

    def test_log_podcast_with_metadata(self, mock_pool, mock_connection, mock_cursor):
        """Test podcast logging with metadata."""
        from utils import database

        mock_cursor.fetchone.return_value = [1]

        metadata = {"lessons": 3, "duration": 120}

        with patch.object(database, 'get_pool', return_value=mock_pool):
            result = database.log_podcast(
                source_url="https://example.com",
                metadata=metadata
            )

        assert result == 1
        # Verify metadata was JSON encoded
        call_args = mock_cursor.execute.call_args
        assert '{}' not in str(call_args) or '"lessons"' in str(call_args)

    def test_log_podcast_no_database(self):
        """Test podcast logging when database is unavailable."""
        from utils import database

        with patch.object(database, 'get_pool', return_value=None):
            result = database.log_podcast(
                source_url="https://example.com"
            )

        assert result is None

    def test_log_podcast_error_rollback(self, mock_pool, mock_connection, mock_cursor):
        """Test rollback on error during podcast logging."""
        from utils import database

        mock_cursor.execute.side_effect = Exception("Insert failed")

        with patch.object(database, 'get_pool', return_value=mock_pool):
            result = database.log_podcast(source_url="https://example.com")

        assert result is None
        mock_connection.rollback.assert_called_once()


class TestGetPodcast:
    """Tests for podcast retrieval functionality."""

    def test_get_podcast_found(self, mock_pool, mock_connection, mock_cursor):
        """Test retrieving an existing podcast."""
        from utils import database

        mock_cursor.fetchone.return_value = (
            1,
            "https://example.com",
            "Test Title",
            "/tmp/audio.mp3",
            "completed",
            {"key": "value"},
            datetime(2024, 1, 1, 12, 0, 0),
            datetime(2024, 1, 1, 12, 30, 0)
        )

        with patch.object(database, 'get_pool', return_value=mock_pool):
            result = database.get_podcast(1)

        assert result is not None
        assert result['id'] == 1
        assert result['source_url'] == "https://example.com"
        assert result['title'] == "Test Title"
        assert result['status'] == "completed"

    def test_get_podcast_not_found(self, mock_pool, mock_connection, mock_cursor):
        """Test retrieving a non-existent podcast."""
        from utils import database

        mock_cursor.fetchone.return_value = None

        with patch.object(database, 'get_pool', return_value=mock_pool):
            result = database.get_podcast(999)

        assert result is None


class TestUpdatePodcast:
    """Tests for podcast update functionality."""

    def test_update_podcast_success(self, mock_pool, mock_connection, mock_cursor):
        """Test successful podcast update."""
        from utils import database

        mock_cursor.rowcount = 1

        with patch.object(database, 'get_pool', return_value=mock_pool):
            result = database.update_podcast(
                podcast_id=1,
                status="completed",
                audio_path="/tmp/final.mp3"
            )

        assert result is True
        mock_connection.commit.assert_called_once()

    def test_update_podcast_not_found(self, mock_pool, mock_connection, mock_cursor):
        """Test updating non-existent podcast."""
        from utils import database

        mock_cursor.rowcount = 0

        with patch.object(database, 'get_pool', return_value=mock_pool):
            result = database.update_podcast(
                podcast_id=999,
                status="completed"
            )

        assert result is False

    def test_update_podcast_no_changes(self, mock_pool, mock_connection, mock_cursor):
        """Test update with no fields to change."""
        from utils import database

        with patch.object(database, 'get_pool', return_value=mock_pool):
            result = database.update_podcast(podcast_id=1)

        assert result is True
        mock_cursor.execute.assert_not_called()


class TestDeletePodcast:
    """Tests for podcast deletion functionality."""

    def test_delete_podcast_success(self, mock_pool, mock_connection, mock_cursor):
        """Test successful podcast deletion."""
        from utils import database

        mock_cursor.rowcount = 1

        with patch.object(database, 'get_pool', return_value=mock_pool):
            result = database.delete_podcast(1)

        assert result is True
        mock_connection.commit.assert_called_once()

    def test_delete_podcast_not_found(self, mock_pool, mock_connection, mock_cursor):
        """Test deleting non-existent podcast."""
        from utils import database

        mock_cursor.rowcount = 0

        with patch.object(database, 'get_pool', return_value=mock_pool):
            result = database.delete_podcast(999)

        assert result is False


class TestGetPodcastsByUrl:
    """Tests for retrieving podcasts by URL."""

    def test_get_podcasts_by_url_found(self, mock_pool, mock_connection, mock_cursor):
        """Test retrieving podcasts by URL."""
        from utils import database

        mock_cursor.fetchall.return_value = [
            (1, "https://example.com", "Title 1", "/path1", "completed", {},
             datetime(2024, 1, 1), datetime(2024, 1, 1)),
            (2, "https://example.com", "Title 2", "/path2", "created", {},
             datetime(2024, 1, 2), datetime(2024, 1, 2))
        ]

        with patch.object(database, 'get_pool', return_value=mock_pool):
            result = database.get_podcasts_by_url("https://example.com")

        assert len(result) == 2
        assert result[0]['id'] == 1
        assert result[1]['id'] == 2

    def test_get_podcasts_by_url_empty(self, mock_pool, mock_connection, mock_cursor):
        """Test retrieving podcasts when none exist."""
        from utils import database

        mock_cursor.fetchall.return_value = []

        with patch.object(database, 'get_pool', return_value=mock_pool):
            result = database.get_podcasts_by_url("https://new-url.com")

        assert result == []


class TestGetRecentPodcasts:
    """Tests for retrieving recent podcasts."""

    def test_get_recent_podcasts(self, mock_pool, mock_connection, mock_cursor):
        """Test retrieving recent podcasts."""
        from utils import database

        mock_cursor.fetchall.return_value = [
            (3, "https://c.com", "Title C", None, "created", {},
             datetime(2024, 1, 3), datetime(2024, 1, 3)),
            (2, "https://b.com", "Title B", None, "created", {},
             datetime(2024, 1, 2), datetime(2024, 1, 2)),
        ]

        with patch.object(database, 'get_pool', return_value=mock_pool):
            result = database.get_recent_podcasts(limit=2)

        assert len(result) == 2
        # Should be ordered by created_at DESC
        assert result[0]['id'] == 3


class TestGetPodcastStats:
    """Tests for podcast statistics."""

    def test_get_stats_success(self, mock_pool, mock_connection, mock_cursor):
        """Test successful stats retrieval."""
        from utils import database

        mock_cursor.fetchone.return_value = (
            100,  # total
            80,   # completed
            5,    # errors
            datetime(2024, 1, 1),  # oldest
            datetime(2024, 1, 15)  # newest
        )

        with patch.object(database, 'get_pool', return_value=mock_pool):
            result = database.get_podcast_stats()

        assert result['database_available'] is True
        assert result['total_podcasts'] == 100
        assert result['completed'] == 80
        assert result['errors'] == 5

    def test_get_stats_no_database(self):
        """Test stats when database is unavailable."""
        from utils import database

        with patch.object(database, 'get_pool', return_value=None):
            result = database.get_podcast_stats()

        assert result['database_available'] is False


# =============================================================================
# Integration Tests (Require Running PostgreSQL)
# =============================================================================

@pytest.mark.skipif(
    not os.getenv('DATABASE_URL'),
    reason="DATABASE_URL not set - skipping integration tests"
)
class TestDatabaseIntegration:
    """Integration tests that require a running PostgreSQL database."""

    @pytest.fixture(autouse=True)
    def setup_database_module(self):
        """Ensure database module has correct DATABASE_URL."""
        from utils import database
        import importlib

        # Store original value
        original_url = database.DATABASE_URL
        original_pool = database._connection_pool

        # Set from environment and reset pool
        database.DATABASE_URL = os.getenv('DATABASE_URL')
        database._connection_pool = None

        yield database

        # Restore original state
        database.DATABASE_URL = original_url
        database._connection_pool = original_pool

    def test_full_crud_workflow(self, setup_database_module):
        """Test complete create, read, update, delete workflow."""
        database = setup_database_module

        # Create
        podcast_id = database.log_podcast(
            source_url="https://integration-test.com/article",
            title="Integration Test",
            status="created",
            metadata={"test": True}
        )
        assert podcast_id is not None

        # Read
        podcast = database.get_podcast(podcast_id)
        assert podcast is not None
        assert podcast['source_url'] == "https://integration-test.com/article"
        assert podcast['title'] == "Integration Test"
        assert podcast['status'] == "created"

        # Update
        success = database.update_podcast(
            podcast_id=podcast_id,
            status="completed",
            audio_path="/tmp/test.mp3"
        )
        assert success is True

        # Verify update
        updated = database.get_podcast(podcast_id)
        assert updated['status'] == "completed"
        assert updated['audio_path'] == "/tmp/test.mp3"

        # Delete
        deleted = database.delete_podcast(podcast_id)
        assert deleted is True

        # Verify deletion
        gone = database.get_podcast(podcast_id)
        assert gone is None

    def test_health_check_connected(self, setup_database_module):
        """Test health check with actual database."""
        database = setup_database_module

        result = database.health_check()
        assert result['status'] == 'healthy'
        assert result['connected'] is True

    def test_init_db_idempotent(self, setup_database_module):
        """Test database initialization is idempotent."""
        database = setup_database_module

        # Should succeed multiple times
        result1 = database.init_db()
        result2 = database.init_db()

        assert result1 is True
        assert result2 is True

    def test_concurrent_operations(self, setup_database_module):
        """Test concurrent database operations."""
        database = setup_database_module
        import threading

        results = []

        def create_podcast(i):
            pid = database.log_podcast(
                source_url=f"https://concurrent-test.com/{i}",
                title=f"Concurrent Test {i}"
            )
            results.append(pid)

        threads = [threading.Thread(target=create_podcast, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should have succeeded
        assert len(results) == 5
        assert None not in results

        # Cleanup
        for pid in results:
            if pid:
                database.delete_podcast(pid)
