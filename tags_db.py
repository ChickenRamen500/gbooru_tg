"""Separate SQLite database for Gelbooru tag metadata.

Stored in data/tags.db — separate from the main bot.db so that a main-DB
reset never loses the tag type information.

Tag types from Gelbooru API (field "type" in s=tag responses):
    0 = general
    1 = artist
    3 = copyright
    4 = character
    5 = circle / meta
    6 = meta (deprecated/other)

We map them to 5 display categories: artist, character, copyright, meta, general.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TAGS_DB_PATH = Path(__file__).parent / "data" / "tags.db"

# Gelbooru type -> display category
TYPE_MAP: dict[int, str] = {
    0: "general",
    1: "artist",
    3: "copyright",
    4: "character",
    5: "meta",
    6: "meta",
}

# Display order (most important first)
CATEGORY_ORDER = ["artist", "copyright", "character", "meta", "general"]


def init_tags_db() -> None:
    """Create the tags database if it doesn't exist."""
    TAGS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(TAGS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            name       TEXT PRIMARY KEY,
            type       INTEGER NOT NULL DEFAULT 0,
            count      INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    # Index for autocomplete (prefix search ordered by popularity)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)"
    )
    conn.commit()
    conn.close()
    logger.info("Tags database ready at %s", TAGS_DB_PATH)


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(TAGS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def upsert_tags(tags: list[dict[str, Any]]) -> int:
    """Bulk insert/update a list of tag dicts ({name, type, count}).

    Returns the number of newly inserted rows (updates are not counted).
    """
    if not tags:
        return 0
    conn = _get_conn()
    cursor = conn.cursor()
    inserted = 0
    for tag in tags:
        name = tag.get("name", "").strip()
        if not name:
            continue
        tag_type = int(tag.get("type", 0) or 0)
        count = int(tag.get("count", 0) or 0)
        try:
            cursor.execute(
                "INSERT INTO tags (name, type, count, updated_at) "
                "VALUES (?, ?, ?, datetime('now')) "
                "ON CONFLICT(name) DO UPDATE SET "
                "type = excluded.type, count = excluded.count, "
                "updated_at = datetime('now')",
                (name, tag_type, count),
            )
            inserted += cursor.rowcount  # 1 for insert, 1 for update-on-conflict path
        except sqlite3.Error as e:
            logger.warning("Failed to upsert tag %r: %s", name, e)
    conn.commit()
    conn.close()
    return inserted


def get_tag_types(names: list[str]) -> dict[str, int]:
    """Batch-lookup tag types from the local DB.

    Returns {name: type} for tags that exist locally.
    """
    if not names:
        return {}
    # Deduplicate and filter empties
    unique = list({n.strip() for n in names if n and n.strip()})
    if not unique:
        return {}

    result: dict[str, int] = {}
    conn = _get_conn()
    cursor = conn.cursor()
    # SQLite has a variable limit (~999); chunk to be safe
    chunk_size = 500
    for i in range(0, len(unique), chunk_size):
        batch = unique[i : i + chunk_size]
        placeholders = ",".join("?" * len(batch))
        cursor.execute(
            f"SELECT name, type FROM tags WHERE name IN ({placeholders})",
            batch,
        )
        for row in cursor.fetchall():
            result[row["name"]] = row["type"]
    conn.close()
    return result


def categorize_tags(names: list[str]) -> dict[str, list[str]]:
    """Split tag names into display categories using the local DB.

    Returns {"artist": [...], "character": [...], "copyright": [...],
    "meta": [...], "general": [...]}.
    Tags not found in the DB go into "general" as a fallback.
    """
    categories: dict[str, list[str]] = {c: [] for c in CATEGORY_ORDER}
    if not names:
        return categories

    types = get_tag_types(names)
    for name in names:
        name = name.strip()
        if not name:
            continue
        tag_type = types.get(name)
        category = TYPE_MAP.get(tag_type, "general") if tag_type is not None else "general"
        categories.setdefault(category, []).append(name)
    return categories


def autocomplete(prefix: str, limit: int = 10) -> list[dict[str, Any]]:
    """Return tags whose name starts with *prefix*, ordered by popularity.

    Pure local query — zero API calls.
    """
    prefix = prefix.strip().lower()
    if not prefix:
        return []
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, type, count FROM tags "
        "WHERE name LIKE ? "
        "ORDER BY count DESC, name ASC "
        "LIMIT ?",
        (prefix + "%", limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"name": row["name"], "type": row["type"], "count": row["count"]}
        for row in rows
    ]


def get_tags_count() -> int:
    """Return total number of tags stored locally."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as c FROM tags")
    row = cursor.fetchone()
    conn.close()
    return row["c"] if row else 0
