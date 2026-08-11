"""SQLite database module for the bot."""

import asyncio
import logging
import sqlite3
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "bot.db"


def init_db() -> None:
    """Initialize the database with all required tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id    INTEGER PRIMARY KEY,
            username   TEXT,
            role       TEXT NOT NULL DEFAULT 'user',
            added_at   TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # Saved searches table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_searches (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            tags       TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, tags)
        )
    """)

    # Saved posts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_posts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            post_id    INTEGER NOT NULL,
            tags       TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, post_id)
        )
    """)

    # Blacklist table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            tag        TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, tag)
        )
    """)

    # Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            user_id    INTEGER PRIMARY KEY,
            rating     TEXT NOT NULL DEFAULT 'safe',
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # Recent queries table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recent_queries (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            tags_hash  TEXT NOT NULL,
            tags       TEXT NOT NULL,
            last_used  TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, tags_hash)
        )
    """)

    # Post status cache table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS post_status (
            post_id    INTEGER PRIMARY KEY,
            status     TEXT NOT NULL DEFAULT 'alive',
            checked_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {DB_PATH}")


def get_connection() -> sqlite3.Connection:
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


async def get_user(user_id: int) -> Optional[dict[str, Any]]:
    """Get user by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


async def add_user(user_id: int, username: Optional[str] = None, role: str = "user") -> bool:
    """Add or update a user. Returns True if inserted, False if updated."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (user_id, username, role) VALUES (?, ?, ?)",
            (user_id, username, role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        cursor.execute(
            "UPDATE users SET username = ?, role = ? WHERE user_id = ?",
            (username, role, user_id)
        )
        conn.commit()
        return False
    finally:
        conn.close()


async def update_user_role(user_id: int, role: str) -> bool:
    """Update user role. Returns True if user exists."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


async def get_all_users() -> list[dict[str, Any]]:
    """Get all users."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY added_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


async def get_user_setting(user_id: int, key: str, default: Any = None) -> Any:
    """Get a user setting value."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM settings WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row and key in row.keys():
        return row[key]
    return default


async def set_user_setting(user_id: int, key: str, value: Any) -> None:
    """Set a user setting value using UPSERT."""
    conn = get_connection()
    cursor = conn.cursor()
    if key == "rating":
        cursor.execute(
            "INSERT INTO settings (user_id, rating) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET rating = excluded.rating",
            (user_id, value)
        )
        conn.commit()
    conn.close()


async def get_user_rating(user_id: int) -> str:
    """Get user's default rating setting."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT rating FROM settings WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row["rating"]
    return "safe"


async def save_recent_query(user_id: int, tags: str) -> int:
    """Save or update recent query, return query ID."""
    import hashlib
    tags_hash = hashlib.md5(f"{user_id}:{tags}".encode()).hexdigest()

    conn = get_connection()
    cursor = conn.cursor()

    # Check if exists
    cursor.execute(
        "SELECT id FROM recent_queries WHERE user_id = ? AND tags_hash = ?",
        (user_id, tags_hash)
    )
    row = cursor.fetchone()

    if row:
        query_id = row["id"]
        cursor.execute(
            "UPDATE recent_queries SET last_used = datetime('now') WHERE id = ?",
            (query_id,)
        )
    else:
        cursor.execute(
            "INSERT INTO recent_queries (user_id, tags_hash, tags) VALUES (?, ?, ?)",
            (user_id, tags_hash, tags)
        )
        query_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return query_id


async def get_recent_query(query_id: int) -> Optional[dict[str, Any]]:
    """Get recent query by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recent_queries WHERE id = ?", (query_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


async def save_search(user_id: int, tags: str) -> tuple[bool, str]:
    """Save a search. Returns (success, message)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO saved_searches (user_id, tags) VALUES (?, ?)",
            (user_id, tags)
        )
        conn.commit()
        return True, "✅ Поиск сохранён"
    except sqlite3.IntegrityError:
        return False, "Поиск уже сохранён"
    finally:
        conn.close()


async def get_saved_searches(user_id: int) -> list[dict[str, Any]]:
    """Get all saved searches for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM saved_searches WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


async def delete_saved_search(search_id: int, user_id: int) -> bool:
    """Delete a saved search."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM saved_searches WHERE id = ? AND user_id = ?",
        (search_id, user_id)
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


async def save_post(user_id: int, post_id: int, tags: Optional[str] = None) -> tuple[bool, str]:
    """Save a post. Returns (success, message)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO saved_posts (user_id, post_id, tags) VALUES (?, ?, ?)",
            (user_id, post_id, tags)
        )
        conn.commit()
        return True, "✅ Пост сохранён"
    except sqlite3.IntegrityError:
        return False, "Пост уже сохранён"
    finally:
        conn.close()


async def get_saved_posts(user_id: int, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    """Get saved posts for a user with pagination."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM saved_posts WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (user_id, limit, offset)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


async def delete_saved_post(post_id: int, user_id: int) -> bool:
    """Delete a saved post."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM saved_posts WHERE post_id = ? AND user_id = ?",
        (post_id, user_id)
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


async def get_blacklist(user_id: int) -> list[dict[str, Any]]:
    """Get user's blacklist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM blacklist WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


async def add_to_blacklist(user_id: int, tag: str) -> tuple[bool, str]:
    """Add a tag to blacklist. Returns (success, message)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO blacklist (user_id, tag) VALUES (?, ?)",
            (user_id, tag)
        )
        conn.commit()
        return True, f"✅ Тег '{tag}' добавлен в чёрный список"
    except sqlite3.IntegrityError:
        return False, f"Тег '{tag}' уже в чёрном списке"
    finally:
        conn.close()


async def remove_from_blacklist(blacklist_id: int, user_id: int) -> bool:
    """Remove a tag from blacklist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM blacklist WHERE id = ? AND user_id = ?",
        (blacklist_id, user_id)
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


async def update_post_status(post_id: int, status: str) -> None:
    """Update post status cache."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO post_status (post_id, status, checked_at) VALUES (?, ?, datetime('now')) "
        "ON CONFLICT(post_id) DO UPDATE SET status = excluded.status, checked_at = datetime('now')",
        (post_id, status)
    )
    conn.commit()
    conn.close()


async def get_post_status(post_id: int) -> Optional[dict[str, Any]]:
    """Get post status from cache."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM post_status WHERE post_id = ?", (post_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None
