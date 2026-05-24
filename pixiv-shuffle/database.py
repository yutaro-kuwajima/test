import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "pixiv.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS authors (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                followed_at TEXT,
                fetched_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS works (
                id            TEXT PRIMARY KEY,
                author_id     TEXT NOT NULL,
                title         TEXT,
                image_url     TEXT,
                page_url      TEXT,
                created_at    TEXT,
                fetched_at    TEXT,
                seen          INTEGER DEFAULT 0,
                last_shown_at TEXT,
                shown_count   INTEGER DEFAULT 0,
                FOREIGN KEY (author_id) REFERENCES authors(id)
            );
        """)


# ---------- Author CRUD ----------

def upsert_author(author_id: str, name: str, followed_at: str | None = None):
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO authors (id, name, followed_at, fetched_at)
            VALUES (?, ?, ?, NULL)
            ON CONFLICT(id) DO UPDATE SET name = excluded.name
            """,
            (author_id, name, followed_at),
        )


def update_author_fetched_at(author_id: str):
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE authors SET fetched_at = ? WHERE id = ?",
            (now, author_id),
        )


def get_all_authors() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM authors").fetchall()


def get_authors_to_fetch(limit: int = 50) -> list[sqlite3.Row]:
    """Return authors ordered by fetched_at ASC (oldest first), limited."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM authors ORDER BY fetched_at ASC NULLS FIRST LIMIT ?",
            (limit,),
        ).fetchall()


# ---------- Work CRUD ----------

def upsert_work(
    work_id: str,
    author_id: str,
    title: str,
    image_url: str,
    page_url: str,
    created_at: str,
):
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO works
                (id, author_id, title, image_url, page_url, created_at, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (work_id, author_id, title, image_url, page_url, created_at, now),
        )


def get_random_work(exclude_author_id: str | None = None) -> sqlite3.Row | None:
    import random
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=30)).isoformat()

    r = random.random()

    def _fetch(where_clause: str, params: list) -> sqlite3.Row | None:
        exclude_clause = ""
        if exclude_author_id:
            exclude_clause = " AND author_id != ?"
            params = params + [exclude_author_id]
        sql = f"""
            SELECT * FROM works
            WHERE {where_clause}{exclude_clause}
            ORDER BY RANDOM()
            LIMIT 1
        """
        with get_conn() as conn:
            row = conn.execute(sql, params).fetchone()
        return row

    if r < 0.70:
        row = _fetch("seen = 0", [])
    elif r < 0.95:
        row = _fetch("last_shown_at < ? OR (seen = 1 AND last_shown_at IS NULL)", [cutoff])
    else:
        row = _fetch("1 = 1", [])

    # Fallback: any work regardless of filters
    if row is None:
        row = _fetch("1 = 1", [])

    return row


def mark_seen(work_id: str):
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE works
            SET seen = 1,
                last_shown_at = ?,
                shown_count = shown_count + 1
            WHERE id = ?
            """,
            (now, work_id),
        )


def mark_skipped(work_id: str):
    """Keep seen=0 but update last_shown_at so it won't appear immediately."""
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE works SET last_shown_at = ? WHERE id = ?",
            (now, work_id),
        )


def get_stats() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM works").fetchone()[0]
        unseen = conn.execute("SELECT COUNT(*) FROM works WHERE seen = 0").fetchone()[0]
        authors = conn.execute("SELECT COUNT(*) FROM authors").fetchone()[0]
    return {"total": total, "unseen": unseen, "authors": authors}


def work_id_exists(work_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM works WHERE id = ?", (work_id,)).fetchone()
    return row is not None
