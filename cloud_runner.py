"""
cloud_runner.py — 24/7 Azure Cloud Monitor
===========================================
This is the script that runs non-stop on Azure.

It does 3 things on a schedule:
  1. Every 30 min  — Search for new jobs and email alerts
  2. Every morning — Check follow-up reminders
  3. Every Sunday  — Send weekly progress digest

Run locally to test:  python cloud_runner.py
Deploy to Azure:      docker build + az container create

All output is logged to stdout (visible in Azure Container logs).
"""

import os
import json
import time
import schedule
import logging
from datetime import datetime

# ─── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("JobAgent")

# ─── Load search config from environment ──────────────────────────────────────
SEARCH_KEYWORDS  = os.environ.get("SEARCH_KEYWORDS",  "software engineer")
SEARCH_LOCATION  = os.environ.get("SEARCH_LOCATION",  "")
SEARCH_INDUSTRY  = os.environ.get("SEARCH_INDUSTRY",  "tech startup")
CHECK_INTERVAL   = int(os.environ.get("CHECK_INTERVAL_MINUTES", "30"))
MAX_DAYS_OLD     = int(os.environ.get("MAX_JOB_AGE_DAYS", "1"))

# Support Azure File Share mount — set DATA_DIR env var to /mnt/azurefile in production
_DATA_DIR        = os.environ.get("DATA_DIR", ".")
SAVED_JOBS_FILE  = os.path.join(_DATA_DIR, "saved_jobs.json")
SEEN_JOBS_FILE   = os.path.join(_DATA_DIR, "seen_jobs.json")


# ─── Helpers ───────────────────────────────────────────────────────────────────
def load_seen_jobs() -> set:
    if os.path.exists(SEEN_JOBS_FILE):
        try:
            with open(SEEN_JOBS_FILE) as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen_jobs(seen: set):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen), f)

def load_saved_jobs() -> list:
    if not os.path.exists(SAVED_JOBS_FILE):
        return []
    try:
        with open(SAVED_JOBS_FILE) as f:
            return json.load(f)
    except Exception:
        return []

def make_job_key(job: dict) -> str:
    """Create a unique fingerprint for a job to avoid duplicates."""
    title   = job.get("title", "").lower().strip()
    company = job.get("company", "").lower().strip()
    return f"{title}::{company}"


# ─── Job Search ────────────────────────────────────────────────────────────────
def run_job_search() -> list:
    """
    Run the agent and return newly found jobs (not seen before).
    """
    from job_agent import run_agent

    log.info(f"🔍 Searching for: '{SEARCH_KEYWORDS}' in '{SEARCH_LOCATION or 'anywhere'}'")

    goal = f"""
    Search for '{SEARCH_KEYWORDS}' jobs posted in the last {MAX_DAYS_OLD} day(s).
    {"Location: " + SEARCH_LOCATION if SEARCH_LOCATION else "Include remote jobs."}
    Also search RemoteOK and Wellfound for startup roles.
    Also find small {SEARCH_INDUSTRY} companies via Google Maps that might be hiring.
    Save any promising jobs you find.
    Return a summary of what you found.
    """

    try:
        run_agent(goal, verbose=False)
        log.info("✅ Agent search complete")
    except Exception as e:
        log.error(f"Agent error: {e}")

    # Find jobs saved since this run started
    all_jobs  = load_saved_jobs()
    seen      = load_seen_jobs()
    new_jobs  = []

    for job in all_jobs:
        key = make_job_key(job)
        if key not in seen:
            new_jobs.append(job)
            seen.add(key)

    save_seen_jobs(seen)

    if new_jobs:
        log.info(f"🎯 Found {len(new_jobs)} NEW job(s)")
    else:
        log.info("No new jobs this cycle")

    return new_jobs


# ─── Scheduled Tasks ───────────────────────────────────────────────────────────
def task_check_jobs():
    """Scheduled: search for new jobs and email if found."""
    log.info("=" * 50)
    log.info("TASK: Checking for new jobs")

    try:
        from notifications import notify_new_jobs, check_config

        cfg = check_config()
        if not cfg["ready"]:
            log.warning("Email not configured — results won't be emailed")

        new_jobs = run_job_search()

        if new_jobs and cfg["ready"]:
            sent = notify_new_jobs(new_jobs, SEARCH_KEYWORDS)
            if sent:
                log.info(f"📧 Email alert sent for {len(new_jobs)} new job(s)")
        elif new_jobs:
            log.info(f"Found {len(new_jobs)} new jobs (email not configured)")

    except Exception as e:
        log.error(f"Job check task failed: {e}", exc_info=True)


def task_check_followups():
    """Scheduled: check who needs a follow-up and email reminders."""
    log.info("TASK: Checking follow-up reminders")

    try:
        from reminders import load_jobs, get_followup_due
        from notifications import notify_followup_due, check_config

        cfg  = check_config()
        jobs = load_jobs()
        due  = get_followup_due(jobs, days=7)

        if due:
            log.info(f"🔔 {len(due)} job(s) need follow-up")
            if cfg["ready"]:
                notify_followup_due(due)
                log.info("📧 Follow-up reminder email sent")
        else:
            log.info("No follow-ups needed today")

    except Exception as e:
        log.error(f"Follow-up task failed: {e}", exc_info=True)


def task_weekly_digest():
    """Scheduled: send weekly progress summary every Sunday."""
    if datetime.now().weekday() != 6:  # 6 = Sunday
        return

    log.info("TASK: Sending weekly digest")

    try:
        from notifications import notify_weekly_digest, check_config

        cfg  = check_config()
        jobs = load_saved_jobs()

        if jobs and cfg["ready"]:
            notify_weekly_digest(jobs)
            log.info("📧 Weekly digest sent")
        elif not cfg["ready"]:
            log.info("Weekly digest skipped (email not configured)")

    except Exception as e:
        log.error(f"Weekly digest task failed: {e}", exc_info=True)


# ─── Health Check ──────────────────────────────────────────────────────────────
def print_status():
    """Print current agent status to logs."""
    jobs = load_saved_jobs()
    counts = {}
    for job in jobs:
        s = job.get("status", "Saved")
        counts[s] = counts.get(s, 0) + 1

    log.info(
        f"STATUS | Saved:{len(jobs)} "
        f"Applied:{counts.get('Applied',0)} "
        f"Interview:{counts.get('Interview',0)} "
        f"Offer:{counts.get('Offer',0)}"
    )


# ─── Main ──────────────────────────────────────────────────────────────────────
def main():
    log.info("=" * 60)
    log.info("🤖 AI JOB SEARCH AGENT — CLOUD MODE STARTED")
    data_dir = os.environ.get("DATA_DIR", ".")
    if data_dir == ".":
        log.warning("⚠️  DATA_DIR not set — jobs saved to container disk (lost on restart)")
        log.warning("   Set DATA_DIR=/mnt/azurefile after mounting an Azure File Share")
    else:
        log.info(f"✅ Data directory: {data_dir} (persistent storage)")
    log.info(f"   Keywords:  {SEARCH_KEYWORDS}")
    log.info(f"   Location:  {SEARCH_LOCATION or 'Anywhere / Remote'}")
    log.info(f"   Industry:  {SEARCH_INDUSTRY}")
    log.info(f"   Interval:  Every {CHECK_INTERVAL} minutes")
    log.info(f"   Max age:   {MAX_DAYS_OLD} day(s)")
    log.info("=" * 60)

    # Verify email on startup
    try:
        from notifications import check_config, send_test_email
        cfg = check_config()
        if cfg["ready"]:
            log.info(f"📧 Email configured: {cfg['from']} → {cfg['to']}")
            send_test_email()
            log.info("✅ Startup test email sent!")
        else:
            log.warning("⚠️  Email not configured — running without notifications")
    except Exception as e:
        log.error(f"Notification setup error: {e}")

    # Run immediately on start
    task_check_jobs()
    task_check_followups()

    # Schedule recurring tasks
    schedule.every(CHECK_INTERVAL).minutes.do(task_check_jobs)
    schedule.every().day.at("09:00").do(task_check_followups)
    schedule.every().day.at("09:00").do(task_weekly_digest)
    schedule.every(6).hours.do(print_status)

    log.info(f"📅 Scheduled: job search every {CHECK_INTERVAL} min, reminders at 9am daily")
    log.info("Agent running... (Ctrl+C to stop)\n")

    # Keep running forever
    while True:
        try:
            schedule.run_pending()
            time.sleep(30)
        except KeyboardInterrupt:
            log.info("Agent stopped by user.")
            break
        except Exception as e:
            log.error(f"Scheduler error: {e}", exc_info=True)
            time.sleep(60)  # Wait and retry


if __name__ == "__main__":
    main()
