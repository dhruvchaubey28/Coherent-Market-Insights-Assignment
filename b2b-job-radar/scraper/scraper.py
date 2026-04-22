"""
scraper.py
----------
Fetches job postings from RemoteOK's public JSON API.
RemoteOK provides a free, public JSON feed — no login required.
We treat each job post as a data point useful for B2B signals
(e.g., which companies are hiring, what tech stacks are trending).
"""

import requests
import json
import time
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REMOTEOK_URL = "https://remoteok.com/api"
HEADERS = {
    # RemoteOK requires a User-Agent that isn't a plain bot string
    "User-Agent": "Mozilla/5.0 (compatible; B2BJobRadar/1.0)"
}
RAW_OUTPUT_PATH = Path(__file__).parent.parent / "data" / "raw_jobs.json"


def fetch_jobs() -> list[dict]:
    """
    Fetches job listings from RemoteOK API.
    Returns a list of raw job dicts.
    Handles rate limits and errors gracefully.
    """
    logger.info("Fetching jobs from RemoteOK...")
    try:
        response = requests.get(REMOTEOK_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()

        data = response.json()

        # First item is a legal notice/meta object — skip it
        jobs = [item for item in data if isinstance(item, dict) and item.get("id") and item.get("id") != "legal"]
        logger.info(f"Fetched {len(jobs)} raw job records.")
        return jobs

    except requests.exceptions.Timeout:
        logger.error("Request timed out.")
        return []
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e}")
        return []
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON response.")
        return []
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return []


def save_raw(jobs: list[dict]):
    """Saves raw fetched jobs to a JSON file for audit/debug purposes."""
    RAW_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_OUTPUT_PATH, "w") as f:
        json.dump({"fetched_at": datetime.utcnow().isoformat(), "jobs": jobs}, f, indent=2)
    logger.info(f"Raw data saved to {RAW_OUTPUT_PATH}")


if __name__ == "__main__":
    jobs = fetch_jobs()
    save_raw(jobs)
    print(f"Done. {len(jobs)} jobs fetched.")


# ── Seed data for local testing without internet ──────────────────────────────

SEED_JOBS = [
    {"id": "1001", "position": "Senior Backend Engineer", "company": "Stripe", "location": "Remote USA", "tags": ["python", "django", "postgresql", "aws"], "salary_min": 140000, "salary_max": 180000, "apply": "https://stripe.com/jobs", "description": "<p>Join Stripe's backend team to build payment infrastructure used by millions.</p>", "date": "1713571200"},
    {"id": "1002", "position": "Data Engineer", "company": "Shopify", "location": "Remote Canada", "tags": ["python", "spark", "kafka", "dbt"], "salary_min": 120000, "salary_max": 160000, "apply": "https://shopify.com/careers", "description": "<p>Build data pipelines powering Shopify's merchant analytics.</p>", "date": "1713484800"},
    {"id": "1003", "position": "DevOps Engineer", "company": "Cloudflare", "location": "Remote Global", "tags": ["kubernetes", "terraform", "go", "linux"], "salary_min": 130000, "salary_max": 170000, "apply": "https://cloudflare.com/careers", "description": "<p>Manage global infrastructure serving millions of requests per second.</p>", "date": "1713398400"},
    {"id": "1004", "position": "Full Stack Developer", "company": "Linear", "location": "Remote", "tags": ["react", "typescript", "nodejs", "graphql"], "salary_min": 110000, "salary_max": 150000, "apply": "https://linear.app/careers", "description": "<p>Build the future of project management tools for software teams.</p>", "date": "1713312000"},
    {"id": "1005", "position": "ML Engineer", "company": "Hugging Face", "location": "Remote Europe", "tags": ["python", "pytorch", "transformers", "cuda"], "salary_min": 150000, "salary_max": 200000, "apply": "https://huggingface.co/jobs", "description": "<p>Work on open-source AI tooling used by the global ML community.</p>", "date": "1713225600"},
    {"id": "1006", "position": "Platform Engineer", "company": "Vercel", "location": "Remote", "tags": ["nodejs", "rust", "kubernetes", "edge"], "salary_min": 135000, "salary_max": 175000, "apply": "https://vercel.com/careers", "description": "<p>Build the deployment platform powering the frontend ecosystem.</p>", "date": "1713139200"},
    {"id": "1007", "position": "Backend Engineer – Payments", "company": "Brex", "location": "Remote USA", "tags": ["golang", "grpc", "postgresql", "aws"], "salary_min": 145000, "salary_max": 190000, "apply": "https://brex.com/careers", "description": "<p>Scale Brex's financial infrastructure for enterprise customers.</p>", "date": "1713052800"},
    {"id": "1008", "position": "Data Analyst", "company": "Notion", "location": "Remote", "tags": ["sql", "python", "looker", "data analysis"], "salary_min": 95000, "salary_max": 130000, "apply": "https://notion.so/jobs", "description": "<p>Turn product data into insights that shape Notion's roadmap.</p>", "date": "1712966400"},
    {"id": "1009", "position": "Site Reliability Engineer", "company": "PlanetScale", "location": "Remote", "tags": ["kubernetes", "vitess", "mysql", "golang"], "salary_min": 140000, "salary_max": 180000, "apply": "https://planetscale.com/careers", "description": "<p>Ensure 99.99% uptime for the world's most scalable MySQL platform.</p>", "date": "1712880000"},
    {"id": "1010", "position": "Frontend Engineer", "company": "Figma", "location": "Remote USA", "tags": ["react", "typescript", "webgl", "css"], "salary_min": 130000, "salary_max": 170000, "apply": "https://figma.com/careers", "description": "<p>Build collaborative design tools used by millions of designers worldwide.</p>", "date": "1712793600"},
    {"id": "1011", "position": "Cloud Architect", "company": "HashiCorp", "location": "Remote Global", "tags": ["terraform", "aws", "azure", "gcp"], "salary_min": 160000, "salary_max": 210000, "apply": "https://hashicorp.com/careers", "description": "<p>Design cloud-agnostic infrastructure solutions for enterprise clients.</p>", "date": "1712707200"},
    {"id": "1012", "position": "iOS Engineer", "company": "Revolut", "location": "Remote Europe", "tags": ["swift", "swiftui", "ios", "fintech"], "salary_min": 100000, "salary_max": 140000, "apply": "https://revolut.com/careers", "description": "<p>Build the Revolut app used by 35M+ customers globally.</p>", "date": "1712620800"},
    {"id": "1013", "position": "Security Engineer", "company": "1Password", "location": "Remote Canada", "tags": ["rust", "cryptography", "security", "linux"], "salary_min": 125000, "salary_max": 165000, "apply": "https://1password.com/careers", "description": "<p>Protect the passwords and secrets of millions of users and businesses.</p>", "date": "1712534400"},
    {"id": "1014", "position": "Analytics Engineer", "company": "dbt Labs", "location": "Remote USA", "tags": ["dbt", "sql", "python", "data modeling"], "salary_min": 110000, "salary_max": 150000, "apply": "https://getdbt.com/careers", "description": "<p>Help build the tools that define modern analytics engineering.</p>", "date": "1712448000"},
    {"id": "1015", "position": "Product Engineer", "company": "Loom", "location": "Remote", "tags": ["react", "nodejs", "webrtc", "typescript"], "salary_min": 120000, "salary_max": 155000, "apply": "https://loom.com/careers", "description": "<p>Build async video features that replace unnecessary meetings.</p>", "date": "1712361600"},
]


def get_seed_jobs() -> list[dict]:
    """Return seed jobs for local demo / testing."""
    return SEED_JOBS
