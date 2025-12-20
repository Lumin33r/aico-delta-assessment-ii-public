"""
Minimal PostgreSQL Database Integration

Simple database utilities for logging podcast generation events.
No ORM, no migrations framework - just psycopg2 with connection pooling.
"""

import os
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Optional psycopg2 import - gracefully handle if not installed
try:
    import psycopg2
    from psycopg2 import pool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    logger.warning("psycopg2 not installed - database features disabled")

# Connection pool (initialized lazily)
_connection_pool: Optional[Any] = None

DATABASE_URL = os.getenv("DATABASE_URL")


def get_pool():
    """Get or create connection pool."""
    global _connection_pool

    if not PSYCOPG2_AVAILABLE or not DATABASE_URL:
        return None

    if _connection_pool is None:
        try:
            _connection_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=5,
                dsn=DATABASE_URL
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            return None

    return _connection_pool


@contextmanager
def get_db():
    """
    Context manager for database connections.
    Yields None if database is not configured or unavailable.
    """
    pool = get_pool()

    if pool is None:
        yield None
        return

    conn = None
    try:
        conn = pool.getconn()
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        yield None
    finally:
        if conn is not None:
            pool.putconn(conn)


def init_db() -> bool:
    """
    Initialize database tables if they don't exist.
    Returns True if successful, False otherwise.
    """
    if not PSYCOPG2_AVAILABLE or not DATABASE_URL:
        logger.info("Database not configured - skipping initialization")
        return False

    with get_db() as conn:
        if conn is None:
            return False

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS podcasts (
                        id SERIAL PRIMARY KEY,
                        source_url TEXT NOT NULL,
                        title TEXT,
                        audio_path TEXT,
                        status VARCHAR(50) DEFAULT 'created',
                        metadata JSONB DEFAULT '{}',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    );

                    CREATE INDEX IF NOT EXISTS idx_podcasts_url ON podcasts(source_url);
                    CREATE INDEX IF NOT EXISTS idx_podcasts_created ON podcasts(created_at);
                """)
                conn.commit()
                logger.info("Database tables initialized")
                return True
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            conn.rollback()
            return False


# =============================================================================
# Podcast CRUD Operations
# =============================================================================

def log_podcast(
    source_url: str,
    title: Optional[str] = None,
    audio_path: Optional[str] = None,
    status: str = "created",
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[int]:
    """
    Log a new podcast generation event.
    Returns the podcast ID if successful, None otherwise.
    """
    with get_db() as conn:
        if conn is None:
            logger.debug("Database unavailable - podcast not logged")
            return None

        try:
            import json
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO podcasts (source_url, title, audio_path, status, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (source_url, title, audio_path, status, json.dumps(metadata or {}))
                )
                podcast_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f"Logged podcast {podcast_id}: {source_url}")
                return podcast_id
        except Exception as e:
            logger.error(f"Failed to log podcast: {e}")
            conn.rollback()
            return None


def update_podcast(
    podcast_id: int,
    title: Optional[str] = None,
    audio_path: Optional[str] = None,
    status: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Update an existing podcast record.
    Returns True if successful, False otherwise.
    """
    with get_db() as conn:
        if conn is None:
            return False

        try:
            import json
            updates = []
            values = []

            if title is not None:
                updates.append("title = %s")
                values.append(title)
            if audio_path is not None:
                updates.append("audio_path = %s")
                values.append(audio_path)
            if status is not None:
                updates.append("status = %s")
                values.append(status)
            if metadata is not None:
                updates.append("metadata = %s")
                values.append(json.dumps(metadata))

            if not updates:
                return True  # Nothing to update

            updates.append("updated_at = NOW()")
            values.append(podcast_id)

            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE podcasts SET {', '.join(updates)} WHERE id = %s",
                    values
                )
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to update podcast {podcast_id}: {e}")
            conn.rollback()
            return False


def get_podcast(podcast_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve a podcast by ID.
    Returns podcast dict if found, None otherwise.
    """
    with get_db() as conn:
        if conn is None:
            return None

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, source_url, title, audio_path, status, metadata, created_at, updated_at
                    FROM podcasts WHERE id = %s
                    """,
                    (podcast_id,)
                )
                row = cur.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "source_url": row[1],
                        "title": row[2],
                        "audio_path": row[3],
                        "status": row[4],
                        "metadata": row[5],
                        "created_at": row[6].isoformat() if row[6] else None,
                        "updated_at": row[7].isoformat() if row[7] else None
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to get podcast {podcast_id}: {e}")
            return None


def get_podcasts_by_url(source_url: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve podcasts by source URL.
    Returns list of podcast dicts.
    """
    with get_db() as conn:
        if conn is None:
            return []

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, source_url, title, audio_path, status, metadata, created_at, updated_at
                    FROM podcasts WHERE source_url = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (source_url, limit)
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": row[0],
                        "source_url": row[1],
                        "title": row[2],
                        "audio_path": row[3],
                        "status": row[4],
                        "metadata": row[5],
                        "created_at": row[6].isoformat() if row[6] else None,
                        "updated_at": row[7].isoformat() if row[7] else None
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get podcasts for {source_url}: {e}")
            return []


def get_recent_podcasts(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Retrieve most recent podcasts.
    Returns list of podcast dicts.
    """
    with get_db() as conn:
        if conn is None:
            return []

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, source_url, title, audio_path, status, metadata, created_at, updated_at
                    FROM podcasts
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,)
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": row[0],
                        "source_url": row[1],
                        "title": row[2],
                        "audio_path": row[3],
                        "status": row[4],
                        "metadata": row[5],
                        "created_at": row[6].isoformat() if row[6] else None,
                        "updated_at": row[7].isoformat() if row[7] else None
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get recent podcasts: {e}")
            return []


def delete_podcast(podcast_id: int) -> bool:
    """
    Delete a podcast by ID.
    Returns True if deleted, False otherwise.
    """
    with get_db() as conn:
        if conn is None:
            return False

        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM podcasts WHERE id = %s", (podcast_id,))
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete podcast {podcast_id}: {e}")
            conn.rollback()
            return False


def get_podcast_stats() -> Dict[str, Any]:
    """
    Get database statistics.
    Returns stats dict or empty dict if unavailable.
    """
    with get_db() as conn:
        if conn is None:
            return {"database_available": False}

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                        COUNT(CASE WHEN status = 'error' THEN 1 END) as errors,
                        MIN(created_at) as oldest,
                        MAX(created_at) as newest
                    FROM podcasts
                """)
                row = cur.fetchone()
                return {
                    "database_available": True,
                    "total_podcasts": row[0],
                    "completed": row[1],
                    "errors": row[2],
                    "oldest": row[3].isoformat() if row[3] else None,
                    "newest": row[4].isoformat() if row[4] else None
                }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"database_available": False, "error": str(e)}


def health_check() -> Dict[str, Any]:
    """
    Check database connectivity.
    Returns health status dict.
    """
    if not PSYCOPG2_AVAILABLE:
        return {"status": "unavailable", "reason": "psycopg2 not installed"}

    if not DATABASE_URL:
        return {"status": "unavailable", "reason": "DATABASE_URL not configured"}

    with get_db() as conn:
        if conn is None:
            return {"status": "error", "reason": "Could not connect to database"}

        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return {"status": "healthy", "connected": True}
        except Exception as e:
            return {"status": "error", "reason": str(e)}
