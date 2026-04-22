# B2B Job Radar 

> A live B2B hiring intelligence pipeline — scrapes, cleans, stores, and visualises remote job postings to help businesses track competitor hiring, trending tech stacks, and market signals.

**Live Demo:** _[Add your Render/Railway URL here after deploying]_

---

## The Problem Being Solved

Businesses struggle to keep up with the job market who is hiring, what roles, and with what technology. This is valuable B2B intelligence.

- A **SaaS vendor** wants to know which companies are scaling engineering teams (potential buyers).
- A **recruiter** wants to track which tech stacks are surging in demand.
- A **market analyst** wants to see hiring velocity across sectors.

**B2B Job Radar** solves this by automatically scraping, cleaning, and surfacing remote job data from [RemoteOK](https://remoteok.com) a well-known remote jobs board and presenting it in a searchable, filterable dashboard with aggregate insights.

---

## Architecture

```
RemoteOK Public API
       │
       ▼
┌─────────────┐     ┌──────────────┐     ┌───────────┐
│  scraper.py │────▶│  cleaner.py  │────▶│  jobs.db  │  (SQLite)
└─────────────┘     └──────────────┘     └───────────┘
                                                │
                                         ┌──────────────┐
                                         │   app.py     │  (Flask API)
                                         └──────────────┘
                                                │
                                         ┌──────────────┐
                                         │ index.html   │  (Dashboard)
                                         └──────────────┘
```

The pipeline runs automatically every 6 hours via APScheduler, no manual intervention needed.

---

## Project Structure

```
b2b-job-radar/
├── scraper/
│   └── scraper.py        # Fetches raw data from RemoteOK API
├── cleaner/
│   └── cleaner.py        # Cleans data + writes to SQLite
├── api/
│   └── app.py            # Flask app: API endpoints + scheduler
├── frontend/
│   └── index.html        # Single-page dashboard UI
├── data/                 # Auto-created at runtime (gitignored)
│   ├── jobs.db           # SQLite database
│   └── raw_jobs.json     # Raw scrape output (audit trail)
├── requirements.txt
├── Procfile              # For Render / Railway deployment
├── render.yaml           # One-click Render config
└── README.md
```

---

## Running Locally

### Prerequisites
- Python 3.9+

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/dhruvchaubey28/Coherent-Market-Insights-Assignment.git
cd b2b-job-radar

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the app
python api/app.py
```

Then open **http://localhost:5000** in your browser.

> The scraper runs automatically on startup and every 6 hours after that. You can also click **"↻ Refresh Now"** in the dashboard.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Dashboard UI |
| `GET` | `/api/jobs` | Paginated job list |
| `GET` | `/api/stats` | Top companies, top tags, total count |
| `GET` | `/api/tags` | All unique tech tags |
| `POST` | `/api/refresh` | Manually trigger pipeline |

### Query Parameters for `/api/jobs`

| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default: 1) |
| `per_page` | int | Results per page (max 50, default 20) |
| `search` | string | Full-text search on title, company, description |
| `tag` | string | Filter by a specific tech tag |

---

## Data Pipeline Details

### Phase 1 — Scraping (`scraper/scraper.py`)
- Fetches from `https://remoteok.com/api` (public JSON endpoint, no key needed)
- Skips the first item (legal notice object returned by the API)
- Handles timeouts, HTTP errors, and JSON parse failures gracefully
- Exports raw JSON to `data/raw_jobs.json` for audit purposes

### Phase 2 — Cleaning (`cleaner/cleaner.py`)
Cleaning decisions made:

| Field | Decision |
|-------|----------|
| HTML in descriptions | Stripped with regex |
| Missing company name | Filled with `"Unknown"` |
| Missing location | Filled with `"Remote"` |
| Salary range | Normalised to `"$X – $Y"` string |
| Tags (array) | Joined as comma-separated string |
| Timestamps (epoch) | Converted to `YYYY-MM-DD` |
| Duplicates | Handled via `INSERT OR REPLACE` (upsert by job ID) |

Cleaned data is stored in SQLite (`data/jobs.db`).

### Phase 3 — Automation (`api/app.py`)
- APScheduler runs `scrape → clean → store` every **6 hours** in a background thread
- First run happens **immediately on startup**
- A `POST /api/refresh` endpoint lets you trigger a run manually

---

## Deploying to Render (Free Tier)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — just click **Deploy**
5. Your live URL will appear in the Render dashboard

> **Note:** Render's free tier spins down after inactivity. On the first visit it may take ~30 seconds to wake up.

---

## Environment Variables

No environment variables are required to run this project. The app works out of the box.

> If you later want to use a PostgreSQL database instead of SQLite (recommended for production), add a `DATABASE_URL` environment variable and update `cleaner.py` accordingly.

---

## Tech Stack

| Layer | Tool |
|-------|------|
| Scraping | Python `requests` |
| Storage | SQLite (via `sqlite3`) |
| Backend | Flask |
| Scheduler | APScheduler |
| Frontend | Vanilla HTML/CSS/JS |
| Deployment | Render / Railway |

---

## Trade-offs & Decisions

- **SQLite over PostgreSQL** — Simpler setup for this scope. Zero config, file-based, no external service needed. Easy to swap out later.
- **RemoteOK API over scraping HTML** — RemoteOK provides a clean public JSON API. This is more reliable and respectful than scraping their HTML, and handles pagination implicitly (they return all jobs in one call).
- **APScheduler over Celery/Redis** — For this scale, an in-process scheduler is sufficient and eliminates infrastructure complexity.
- **No AI/ML layer** — Kept out of scope to prioritise reliability of the 3 core phases.
