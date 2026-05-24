import logging
import threading
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles

import config
import database
import pixiv_client
import scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------- Lifespan ----------

@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()

    if not config.PIXIV_REFRESH_TOKEN:
        logger.warning("PIXIV_REFRESH_TOKEN is not set. Pixiv features will be unavailable.")
    else:
        pixiv_client.init_api(config.PIXIV_REFRESH_TOKEN)

    from apscheduler.schedulers.background import BackgroundScheduler
    sched = BackgroundScheduler()
    sched.add_job(
        scheduler.run_batch,
        "cron",
        hour=config.BATCH_HOUR,
        minute=config.BATCH_MINUTE,
        id="daily_batch",
    )
    sched.start()
    logger.info(
        "Scheduler started. Daily batch at %02d:%02d.", config.BATCH_HOUR, config.BATCH_MINUTE
    )

    yield

    sched.shutdown(wait=False)


app = FastAPI(title="Pixiv Shuffle Viewer", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------- Routes ----------

@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/api/next")
async def api_next(exclude_author: str | None = None) -> dict[str, Any]:
    row = database.get_random_work(exclude_author_id=exclude_author)
    if row is None:
        raise HTTPException(status_code=404, detail="No works available. Run a batch fetch first.")
    return {
        "id": row["id"],
        "title": row["title"],
        "author_name": _get_author_name(row["author_id"]),
        "author_id": row["author_id"],
        "image_url": row["image_url"],
        "page_url": row["page_url"],
        "created_at": row["created_at"],
        "seen": bool(row["seen"]),
        "shown_count": row["shown_count"],
    }


@app.post("/api/seen/{work_id}")
async def api_seen(work_id: str) -> dict[str, str]:
    database.mark_seen(work_id)
    return {"status": "ok"}


@app.post("/api/skip/{work_id}")
async def api_skip(work_id: str) -> dict[str, str]:
    database.mark_skipped(work_id)
    return {"status": "ok"}


@app.get("/api/stats")
async def api_stats() -> dict[str, int]:
    return database.get_stats()


@app.post("/api/fetch/trigger")
async def api_fetch_trigger(background_tasks: BackgroundTasks) -> dict[str, str]:
    if not config.PIXIV_REFRESH_TOKEN:
        raise HTTPException(status_code=503, detail="PIXIV_REFRESH_TOKEN is not configured.")
    background_tasks.add_task(_run_batch_safe)
    return {"status": "started"}


async def _run_batch_safe():
    try:
        scheduler.run_batch()
    except Exception:
        logger.exception("Manual batch failed.")


# ---------- Image proxy ----------

@app.get("/api/image_proxy")
async def image_proxy(url: str) -> Response:
    if not url.startswith("https://i.pximg.net/"):
        raise HTTPException(status_code=400, detail="Only i.pximg.net URLs are allowed.")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                url,
                headers={"Referer": "https://www.pixiv.net"},
                timeout=15,
                follow_redirects=True,
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=str(e))
    content_type = resp.headers.get("content-type", "image/jpeg")
    return Response(content=resp.content, media_type=content_type)


# ---------- Helper ----------

def _get_author_name(author_id: str) -> str:
    import sqlite3 as _sqlite3
    with database.get_conn() as conn:
        row = conn.execute("SELECT name FROM authors WHERE id = ?", (author_id,)).fetchone()
    return row["name"] if row else author_id
