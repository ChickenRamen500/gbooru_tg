#!/usr/bin/env python3
"""Standalone script to bulk-populate the tags database from Gelbooru.

Usage:
    python populate_tags.py [TARGET]

Examples:
    python populate_tags.py 50000      # fetch top 50K most popular tags
    python populate_tags.py 100000    # fetch top 100K tags (takes ~3 min)

The script fetches tags ordered by post count (most popular first), so even
a partial run gives you the most useful tags for autocomplete and categorization.

Tags are stored in data/tags.db (separate from the main bot database).
"""

import asyncio
import logging
import sys
from pathlib import Path

# Ensure local imports work when run from the project root
sys.path.insert(0, str(Path(__file__).parent))

import tags_db
from gelbooru import gelbooru_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def populate(target: int) -> None:
    tags_db.init_tags_db()
    existing = tags_db.get_tags_count()
    logger.info("Current tags in DB: %d", existing)

    pages = (target + 99) // 100
    total = 0

    for pid in range(pages):
        tags, api_total = await gelbooru_client.fetch_tags_page(
            pid=pid, limit=100, orderby="count"
        )
        if not tags:
            logger.info("No more tags at page %d (API returned empty)", pid)
            break

        tags_db.upsert_tags(tags)
        total += len(tags)

        if (pid + 1) % 10 == 0:
            logger.info(
                "Progress: %d tags stored (page %d/%d, API reports %d total tags)",
                total, pid + 1, pages, api_total,
            )

        # Stop if API returned fewer than a full page (end of results)
        if len(tags) < 100:
            logger.info("Reached end of results at page %d", pid)
            break

    final_count = tags_db.get_tags_count()
    logger.info("Done. Fetched %d tags this run. DB now has %d tags total.", total, final_count)
    await gelbooru_client.close()


def main() -> None:
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 50000
    asyncio.run(populate(target))


if __name__ == "__main__":
    main()
