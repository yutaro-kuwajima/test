import time
import logging
from datetime import datetime, timezone

import database
import pixiv_client

logger = logging.getLogger(__name__)

BATCH_AUTHOR_LIMIT = 50
SLEEP_BETWEEN_AUTHORS = 1.5  # seconds


def run_batch():
    """Main batch: sync following list and fetch new works."""
    logger.info("Batch started at %s", datetime.now(timezone.utc).isoformat())

    try:
        _sync_following()
    except Exception:
        logger.exception("Failed to sync following list.")

    try:
        _fetch_works()
    except Exception:
        logger.exception("Failed to fetch works.")

    logger.info("Batch finished.")


def _sync_following():
    logger.info("Syncing following list...")
    users = pixiv_client.fetch_all_following()
    for u in users:
        database.upsert_author(u["id"], u["name"])
    logger.info("Synced %d followed users.", len(users))


def _fetch_works():
    authors = database.get_authors_to_fetch(limit=BATCH_AUTHOR_LIMIT)
    logger.info("Fetching works for %d authors.", len(authors))

    for author in authors:
        author_id = author["id"]
        try:
            works = pixiv_client.fetch_user_illusts(author_id, max_works=100)
            new_count = 0
            for w in works:
                if not database.work_id_exists(w["id"]):
                    database.upsert_work(
                        w["id"],
                        w["author_id"],
                        w["title"],
                        w["image_url"],
                        w["page_url"],
                        w["created_at"],
                    )
                    new_count += 1
            database.update_author_fetched_at(author_id)
            logger.info(
                "Author %s (%s): %d new works (total fetched %d).",
                author["name"],
                author_id,
                new_count,
                len(works),
            )
        except Exception:
            logger.exception("Error processing author %s", author_id)

        time.sleep(SLEEP_BETWEEN_AUTHORS)
