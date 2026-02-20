"""
github_runner.py — Runs inside GitHub Actions (one shot, no loop)
"""

import os
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("GHRunner")

SEARCH_KEYWORDS = os.environ.get("SEARCH_KEYWORDS", "software engineer")
SEARCH_LOCATION = os.environ.get("SEARCH_LOCATION", "")
SEARCH_INDUSTRY = os.environ.get("SEARCH_INDUSTRY", "tech startup")
MAX_DAYS_OLD    = int(os.environ.get("MAX_JOB_AGE_DAYS", "1"))
SAVED_JOBS_FILE = "saved_jobs.json"
SEEN_JOBS_FILE  = "seen_jobs.json"


def ensure_files():
    """Create data files if they don't exist yet (first run)."""
    if not os.path.exists(SAVED_JOBS_FILE):
        with open(SAVED_JOBS_FILE, "w") as f:
            json.dump([], f)
        log.info("Created saved_jobs.json")
    if not os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "w") as f:
            json.dump([], f)
        log.info("Created seen_jobs.json")


def load_jobs() -> list:
    try:
        with open(SAVED_JOBS_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def make_key(job: dict) -> str:
    return f"{job.get('title','').lower().strip()}::{job.get('company','').lower().strip()}"


def main():
    log.info("=" * 55)
    log.info("🤖 JOB SEARCH AGENT — GitHub Actions Run")
    log.info(f"   Keywords : {SEARCH_KEYWORDS}")
    log.info(f"   Location : {SEARCH_LOCATION or 'Anywhere / Remote'}")
    log.info(f"   Industry : {SEARCH_INDUSTRY}")
    log.info(f"   Max age  : {MAX_DAYS_OLD} day(s)")
    log.info("=" * 55)

    # Create files on first run
    ensure_files()

    # Verify AI
    try:
        from ai_client import get_client
        ai = get_client()
        log.info(f"AI providers: {ai.status()}")
    except Exception as e:
        log.error(f"AI client failed: {e}")
        raise SystemExit(1)

    # Snapshot before run
    jobs_before     = load_jobs()
    seen_keys_before = set(make_key(j) for j in jobs_before)
    log.info(f"Existing saved jobs: {len(jobs_before)}")

    # Build goal — keep it SHORT to avoid rate limits
    loc_clause = f" in {SEARCH_LOCATION}" if SEARCH_LOCATION else ""
    goal = (
        f"Find new '{SEARCH_KEYWORDS}' jobs{loc_clause} posted today. "
        f"Search job boards and RemoteOK. Save the top 5 best matches."
    )

    log.info(f"Goal: {goal}")

    # Run agent
    try:
        from job_agent import run_agent
        run_agent(goal, verbose=True)
    except Exception as e:
        log.error(f"Agent error: {e}")
        log.info("Checking if any jobs were saved despite the error...")

    # Find new jobs
    jobs_after   = load_jobs()
    new_jobs     = [j for j in jobs_after if make_key(j) not in seen_keys_before]
    log.info(f"New jobs found this run: {len(new_jobs)}")

    # Send email if new jobs found
    if new_jobs:
        try:
            from notifications import notify_new_jobs, check_config
            cfg = check_config()
            if cfg["ready"]:
                sent = notify_new_jobs(new_jobs, SEARCH_KEYWORDS)
                if sent:
                    log.info(f"📧 Email sent for {len(new_jobs)} new job(s)!")
            else:
                log.info("Email not configured — new jobs:")
                for j in new_jobs:
                    log.info(f"  • {j.get('title')} at {j.get('company')}")
        except Exception as e:
            log.warning(f"Email error: {e}")
    else:
        log.info("No new jobs this run")

    # Stats
    counts = {}
    for job in jobs_after:
        s = job.get("status", "Saved")
        counts[s] = counts.get(s, 0) + 1

    log.info("─" * 40)
    log.info(f"Total saved: {len(jobs_after)}")
    for status, count in counts.items():
        log.info(f"  {status}: {count}")
    log.info("─" * 40)
    log.info("✅ Run complete")


if __name__ == "__main__":
    main()
