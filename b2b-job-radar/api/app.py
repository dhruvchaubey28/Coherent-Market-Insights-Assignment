"""
app.py
------
Flask application that:
  1. Serves a REST API over the cleaned jobs DB
  2. Runs the scrape → clean pipeline automatically every 6 hours via APScheduler
  3. Serves the frontend dashboard

Endpoints:
  GET /api/jobs          – paginated job list (filter by tag, company, search)
  GET /api/stats         – aggregate stats (top companies, top tags, total count)
  GET /api/tags          – all unique tags
  POST /api/refresh      – manually trigger a pipeline run (useful for demos)
  GET /                  – serves the HTML dashboard
"""

import logging
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory
from apscheduler.schedulers.background import BackgroundScheduler

# Make sibling modules importable
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scraper"))
sys.path.insert(0, str(ROOT / "cleaner"))

from scraper import fetch_jobs, save_raw
from cleaner import upsert_jobs, get_connection, init_db, DB_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=str(ROOT / "frontend"))

# ── Pipeline ──────────────────────────────────────────────────────────────────

def run_pipeline():
    """Full scrape → clean → store cycle. Falls back to seed data if API unavailable."""
    logger.info("Pipeline started.")
    jobs = fetch_jobs()
    if not jobs:
        logger.warning("Live API unavailable. Loading seed data for demo.")
        from scraper import get_seed_jobs
        jobs = get_seed_jobs()
    if jobs:
        save_raw(jobs)
        count = upsert_jobs(jobs)
        logger.info(f"Pipeline complete. {count} jobs in DB.")
    else:
        logger.warning("Pipeline: no jobs available.")


# ── Scheduler ─────────────────────────────────────────────────────────────────

scheduler = BackgroundScheduler()
scheduler.add_job(run_pipeline, "interval", hours=6, id="pipeline", next_run_time=datetime.now())
scheduler.start()
logger.info("Scheduler started — pipeline runs every 6 hours.")

# ── API helpers ───────────────────────────────────────────────────────────────

def query_db(sql: str, params=()) -> list[dict]:
    try:
        conn = get_connection()
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(str(ROOT / "frontend"), "index.html")


@app.route("/api/jobs")
def get_jobs():
    page     = max(1, int(request.args.get("page", 1)))
    per_page = min(50, int(request.args.get("per_page", 20)))
    search   = request.args.get("search", "").strip()
    tag      = request.args.get("tag", "").strip()
    company  = request.args.get("company", "").strip()
    offset   = (page - 1) * per_page

    where_clauses = []
    params = []

    if search:
        where_clauses.append("(title LIKE ? OR company LIKE ? OR description LIKE ?)")
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    if tag:
        where_clauses.append("tags LIKE ?")
        params.append(f"%{tag}%")
    if company:
        where_clauses.append("company LIKE ?")
        params.append(f"%{company}%")

    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    count_row = query_db(f"SELECT COUNT(*) as cnt FROM jobs {where}", params)
    total = count_row[0]["cnt"] if count_row else 0

    jobs = query_db(
        f"SELECT id, title, company, location, tags, salary, apply_url, posted_date FROM jobs {where} ORDER BY posted_date DESC, scraped_at DESC LIMIT ? OFFSET ?",
        params + [per_page, offset]
    )

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "jobs": jobs
    })


@app.route("/api/stats")
def get_stats():
    total = query_db("SELECT COUNT(*) as cnt FROM jobs")
    top_companies = query_db(
        "SELECT company, COUNT(*) as count FROM jobs WHERE company != 'Unknown' GROUP BY company ORDER BY count DESC LIMIT 10"
    )
    top_tags_raw = query_db("SELECT tags FROM jobs WHERE tags != ''")

    # Count individual tags
    tag_counter: dict[str, int] = {}
    for row in top_tags_raw:
        for t in row["tags"].split(","):
            t = t.strip()
            if t:
                tag_counter[t] = tag_counter.get(t, 0) + 1
    top_tags = sorted(tag_counter.items(), key=lambda x: x[1], reverse=True)[:15]

    return jsonify({
        "total_jobs": total[0]["cnt"] if total else 0,
        "top_companies": top_companies,
        "top_tags": [{"tag": t, "count": c} for t, c in top_tags],
    })


@app.route("/api/tags")
def get_tags():
    rows = query_db("SELECT DISTINCT tags FROM jobs WHERE tags != ''")
    all_tags = set()
    for r in rows:
        for t in r["tags"].split(","):
            t = t.strip()
            if t:
                all_tags.add(t)
    return jsonify(sorted(all_tags))


@app.route("/api/refresh", methods=["POST"])
def manual_refresh():
    """Trigger the pipeline manually (e.g., for demo purposes)."""
    try:
        run_pipeline()
        count = query_db("SELECT COUNT(*) as cnt FROM jobs")
        return jsonify({"status": "ok", "total_jobs": count[0]["cnt"] if count else 0})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    init_db()
    app.run(debug=False, host="0.0.0.0", port=5000)
