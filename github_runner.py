"""
github_runner.py — Runs inside GitHub Actions
==============================================
Lightweight version of cloud_runner.py designed for GitHub Actions.
- No infinite loop (Actions handles scheduling via cron)
- Saves jobs to saved_jobs.json (committed back to repo = free storage)
- Sends email if new jobs found
- Full logging to GitHub Actions console
"""

import os
import json
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("GHRunner")

SEARCH_KEYWORDS = os.environ.get("SEARCH_KEYWORDS", "software engineer")
SEARCH_LOCATION = os.environ.get("SEARCH_LOCATION", "")
SEARCH_INDUSTRY = os.environ.get("SEARCH_INDUSTRY", "tech startup")
MAX_DAYS_OLD    = int(os.environ.get("MAX_JOB_AGE_DAYS", "1"))
SAVED_JOBS_FILE = "saved_jobs.json"
SEEN_JOBS_FILE  = "seen_jobs.json"


def load_seen() -> set:
    try:
        if os.path.exists(SEEN_JOBS_FILE):
            with open(SEEN_JOBS_FILE) as f:
                return set(json.load(f))
    except Exception:
        pass
    return set()


def save_seen(seen: set):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen), f)


def load_jobs() -> list:
    try:
        if os.path.exists(SAVED_JOBS_FILE):
            with open(SAVED_JOBS_FILE) as f:
                return json.load(f)
    except Exception:
        pass
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

    # ── Verify AI client ────────────────────────────────────────
    try:
        from ai_client import get_client
        ai = get_client()
        log.info(f"AI providers: {ai.status()}")
    except Exception as e:
        log.error(f"AI client failed: {e}")
        log.error("Make sure GROQ_API_KEY or GEMINI_API_KEY is set in GitHub Secrets")
        raise SystemExit(1)

    # ── Snapshot jobs before run ────────────────────────────────
    jobs_before = load_jobs()
    seen_before  = load_seen()
    log.info(f"Existing saved jobs: {len(jobs_before)}")

    # ── Run the agent ───────────────────────────────────────────
    from job_agent import run_agent

    # Build goal from env settings
    custom_goal = os.environ.get("INPUT_GOAL", "").strip()

    if custom_goal:
        goal = custom_goal
    else:
        loc_clause = f" in {SEARCH_LOCATION}" if SEARCH_LOCATION else " (remote or anywhere)"
        goal = (
            f"Search for brand new '{SEARCH_KEYWORDS}' jobs{loc_clause} "
            f"posted in the last {MAX_DAYS_OLD} day(s). "
            f"Search job boards, Wellfound, RemoteOK, and Hacker News. "
            f"Also find small {SEARCH_INDUSTRY} companies that might be hiring. "
            f"Save every promising opportunity you find."
        )

    log.info(f"Goal: {goal[:150]}...")
    try:
        summary = run_agent(goal, verbose=True)
    except Exception as e:
        log.error(f"Agent run error: {e}")
        log.info("Agent had an error but may have saved some jobs — continuing...")
        summary = ""

    # ── Find newly added jobs ────────────────────────────────────
    jobs_after = load_jobs()
    seen_after  = set(make_key(j) for j in jobs_before)

    new_jobs = [j for j in jobs_after if make_key(j) not in seen_after]
    log.info(f"New jobs found this run: {len(new_jobs)}")

    # ── Send email if new jobs found ─────────────────────────────
    if new_jobs:
        try:
            from notifications import notify_new_jobs, check_config
            cfg = check_config()
            if cfg["ready"]:
                sent = notify_new_jobs(new_jobs, SEARCH_KEYWORDS)
                if sent:
                    log.info(f"📧 Email alert sent for {len(new_jobs)} new job(s)")
                else:
                    log.warning("Email send failed — check credentials")
            else:
                log.info("Email not configured (set secrets in GitHub repo settings)")
                log.info("New jobs:")
                for job in new_jobs:
                    log.info(f"  • {job.get('title')} at {job.get('company')}")
        except Exception as e:
            log.warning(f"Notification error: {e}")
    else:
        log.info("No new jobs this run — nothing to email")

    # ── Print final stats ────────────────────────────────────────
    total = len(jobs_after)
    counts = {}
    for job in jobs_after:
        s = job.get("status", "Saved")
        counts[s] = counts.get(s, 0) + 1

    log.info("─" * 40)
    log.info(f"Total saved: {total}")
    for status, count in counts.items():
        log.info(f"  {status}: {count}")
    log.info("─" * 40)
    log.info("✅ Run complete")


if __name__ == "__main__":
    main()
