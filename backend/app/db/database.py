import sqlite3
import time
from contextlib import contextmanager

from app.config import settings


def _db_path() -> str:
    return settings.database_url.removeprefix("sqlite:///")


@contextmanager
def _connect():
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                repo_url TEXT NOT NULL,
                status TEXT NOT NULL,
                report_json TEXT,
                created_at REAL NOT NULL
            )
            """
        )


def create_run(run_id: str, repo_url: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO runs (id, repo_url, status, created_at) VALUES (?, ?, 'running', ?)",
            (run_id, repo_url, time.time()),
        )


def update_status(run_id: str, status: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE runs SET status = ? WHERE id = ?", (status, run_id))


def save_report(run_id: str, report_json: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE runs SET status = 'done', report_json = ? WHERE id = ?",
            (report_json, run_id),
        )


def get_run(run_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return dict(row) if row else None