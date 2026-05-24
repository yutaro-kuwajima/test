import time
import logging
from datetime import datetime, timezone

import database
import pixiv_client

logger = logging.getLogger(__name__)

BATCH_AUTHOR_LIMIT = 50
SLEEP_BETWEEN_AUTHORS = 1.5  # seconds

# ---------- Progress state ----------

_progress: dict = {
    "running": False,
    "phase": "",          # "following" | "works" | ""
    "current_author": "",
    "done": 0,
    "total": 0,
    "new_works": 0,
    "started_at": None,
    "finished_at": None,
    "error": None,
}


def get_progress() -> dict:
    return dict(_progress)


def _set(**kwargs):
    _progress.update(kwargs)


# ---------- Batch ----------

def run_batch():
    if _progress["running"]:
        logger.warning("Batch already running, skipping.")
        return

    _set(running=True, phase="", current_author="", done=0, total=0,
         new_works=0, started_at=datetime.now(timezone.utc).isoformat(),
         finished_at=None, error=None)
    logger.info("Batch started at %s", _progress["started_at"])

    try:
        _sync_following()
    except Exception as e:
        logger.exception("Failed to sync following list.")
        _set(error=str(e))

    try:
        _fetch_works()
    except Exception as e:
        logger.exception("Failed to fetch works.")
        _set(error=str(e))

    _set(running=False, phase="", current_author="",
         finished_at=datetime.now(timezone.utc).isoformat())
    logger.info("Batch finished. %d new works added.", _progress["new_works"])


def _sync_following():
    _set(phase="following")
    logger.info("Syncing following list...")
    users = pixiv_client.fetch_all_following()
    for u in users:
        database.upsert_author(u["id"], u["name"])
    logger.info("Synced %d followed users.", len(users))


def _fetch_works():
    authors = database.get_authors_to_fetch(limit=BATCH_AUTHOR_LIMIT)
    _set(phase="works", total=len(authors), done=0)
    logger.info("Fetching works for %d authors.", len(authors))

    for i, author in enumerate(authors):
        author_id = author["id"]
        _set(current_author=author["name"], done=i)
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
            _progress["new_works"] += new_count
            database.update_author_fetched_at(author_id)
            logger.info(
                "Author %s (%s): %d new works (total fetched %d).",
                author["name"], author_id, new_count, len(works),
            )
        except Exception:
            logger.exception("Error processing author %s", author_id)

        time.sleep(SLEEP_BETWEEN_AUTHORS)

    _set(done=len(authors))
