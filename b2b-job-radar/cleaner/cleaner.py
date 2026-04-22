"""
cleaner.py
----------
Cleans raw job data and stores it in SQLite.

Cleaning decisions made:
- Strip HTML tags from description fields
- Normalise salary to a single string (RemoteOK gives salary_min / salary_max)
- Fill missing company names with "Unknown"
- Convert epoch timestamps to ISO date strings
- Deduplicate by job ID (upsert pattern)
- Tags stored as comma-separated string for simplicity
"""

import sqlite3
import re
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "jobs.db"


# ── Helpers ──────────────────────────────────────────────────────────────────

def strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"&[a-z]+;", " ", clean)   # basic HTML entities
    return re.sub(r"\s+", " ", clean).strip()


def safe_str(val, fallback="") -> str:
    return str(val).strip() if val else fallback


def epoch_to_date(val) -> str:
    try:
        return datetime.utcfromtimestamp(int(val)).strftime("%Y-%m-%d")
    except Exception:
        return ""


def normalise_salary(job: dict) -> str:
    lo = job.get("salary_min")
    hi = job.get("salary_max")
    if lo and hi:
        return f"${int(lo):,} – ${int(hi):,}"
    if lo:
        return f"From ${int(lo):,}"
    if hi:
        return f"Up to ${int(hi):,}"
    return "Not disclosed"


def normalise_tags(tags) -> str:
    if not tags:
        return ""
    if isinstance(tags, list):
        return ", ".join(t.strip() for t in tags if t)
    return safe_str(tags)


# ── DB setup ──────────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the jobs table if it doesn't exist."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id              TEXT PRIMARY KEY,
            title           TEXT,
            company         TEXT,
            location        TEXT,
            tags            TEXT,
            salary          TEXT,
            apply_url       TEXT,
            description     TEXT,
            posted_date     TEXT,
            scraped_at      TEXT
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialised.")


# ── Core cleaning & storage ───────────────────────────────────────────────────

def clean_job(raw: dict) -> dict:
    """Transform one raw API record into a clean, flat dict."""
    return {
        "id":           safe_str(raw.get("id"), fallback="unknown"),
        "title":        safe_str(raw.get("position") or raw.get("title"), fallback="Untitled"),
        "company":      safe_str(raw.get("company"), fallback="Unknown"),
        "location":     safe_str(raw.get("location"), fallback="Remote"),
        "tags":         normalise_tags(raw.get("tags")),
        "salary":       normalise_salary(raw),
        "apply_url":    safe_str(raw.get("apply") or raw.get("url")),
        "description":  strip_html(raw.get("description", "")),
        "posted_date":  epoch_to_date(raw.get("date") or raw.get("epoch")),
        "scraped_at":   datetime.utcnow().isoformat(),
    }


def upsert_jobs(jobs: list[dict]) -> int:
    """
    Insert or replace jobs by ID.
    Returns the count of records written.
    """
    init_db()
    conn = get_connection()
    count = 0
    for raw in jobs:
        try:
            clean = clean_job(raw)
            if clean["id"] == "unknown":
                continue
            conn.execute("""
                INSERT OR REPLACE INTO jobs
                  (id, title, company, location, tags, salary, apply_url, description, posted_date, scraped_at)
                VALUES
                  (:id, :title, :company, :location, :tags, :salary, :apply_url, :description, :posted_date, :scraped_at)
            """, clean)
            count += 1
        except Exception as e:
            logger.warning(f"Skipping job due to error: {e}")
    conn.commit()
    conn.close()
    logger.info(f"Upserted {count} jobs into DB.")
    return count


if __name__ == "__main__":
    import json, sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "scraper"))
    from scraper import fetch_jobs
    jobs = fetch_jobs()
    written = upsert_jobs(jobs)
    print(f"Cleaned and stored {written} jobs.")
