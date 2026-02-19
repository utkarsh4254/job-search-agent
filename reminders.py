"""
reminders.py — Follow-up Reminder System
=========================================
• Checks all "Applied" jobs daily
• Alerts when 7 days pass with no response
• Generates a follow-up email to send
• Tracks whether follow-up was sent
"""

import json
import os
from datetime import datetime, timedelta
import anthropic

client = anthropic.Anthropic()
SAVED_JOBS_FILE = "saved_jobs.json"

class C:
    BOLD="\033[1m"; BLUE="\033[94m"; CYAN="\033[96m"; GREEN="\033[92m"
    YELLOW="\033[93m"; RED="\033[91m"; GRAY="\033[90m"; RESET="\033[0m"

def bold(t):   return f"{C.BOLD}{t}{C.RESET}"
def cyan(t):   return f"{C.CYAN}{t}{C.RESET}"
def green(t):  return f"{C.GREEN}{t}{C.RESET}"
def yellow(t): return f"{C.YELLOW}{t}{C.RESET}"
def gray(t):   return f"{C.GRAY}{t}{C.RESET}"
def red(t):    return f"{C.RED}{t}{C.RESET}"
def clear():   os.system("cls" if os.name == "nt" else "clear")
def pause():   input(f"\n  {gray('Press Enter to continue...')}")

def header(sub=""):
    print(f"\n{bold(C.BLUE + '═' * 62 + C.RESET)}")
    print(f"  {bold(cyan('🔔 FOLLOW-UP REMINDERS'))}  {gray(sub)}")
    print(f"{bold(C.BLUE + '═' * 62 + C.RESET)}\n")


def load_jobs() -> list:
    if not os.path.exists(SAVED_JOBS_FILE):
        return []
    with open(SAVED_JOBS_FILE, "r") as f:
        return json.load(f)

def save_jobs(jobs: list):
    for i, j in enumerate(jobs):
        j["id"] = i + 1
    with open(SAVED_JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)


# ─── Check Who Needs Follow-Up ─────────────────────────────────────────────────
def get_followup_due(jobs: list, days: int = 7) -> list:
    """Return jobs that were applied to N+ days ago with no response."""
    due = []
    now = datetime.now()
    cutoff = now - timedelta(days=days)

    for job in jobs:
        if job.get("status") not in ("Applied",):
            continue
        if job.get("followup_sent"):
            continue

        applied_str = job.get("applied_at", "")
        if not applied_str:
            continue

        try:
            applied_dt = datetime.fromisoformat(applied_str[:19])
            days_since = (now - applied_dt).days
            job["_days_since"] = days_since

            if applied_dt <= cutoff:
                due.append(job)
        except ValueError:
            continue

    return sorted(due, key=lambda j: j.get("_days_since", 0), reverse=True)


# ─── Generate Follow-Up Email ──────────────────────────────────────────────────
def generate_followup_email(job: dict) -> str:
    """Use Claude to write a polite follow-up email."""
    prompt = f"""Write a short, polite follow-up email for a job application.

Job: {job['title']}
Company: {job['company']}
Days since applying: {job.get('_days_since', 7)}

Rules:
- Keep it under 100 words
- Be polite and professional, not pushy
- Reference the specific role
- Express continued strong interest
- Ask about timeline/next steps
- End with a clear call to action
- Do NOT use "I hope this email finds you well" or similar clichés
- Sound human and confident

Write the email body only (no subject line)."""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


# ─── Reminders Menu ────────────────────────────────────────────────────────────
def reminders_menu():
    clear()
    header()
    jobs = load_jobs()
    due  = get_followup_due(jobs, days=7)

    if not due:
        print(f"  {green('✅ No follow-ups needed right now!')}\n")
        # Show upcoming
        upcoming = get_followup_due(jobs, days=4)
        if upcoming:
            print(f"  {yellow('📅 Coming up soon (applied 4+ days ago):')}\n")
            for job in upcoming[:5]:
                days_ago = job.get('_days_since', 0)
                print(f"    {yellow('•')} {bold(job['title'])} at {job['company']}"
                      f"  {gray(f'({days_ago} days ago)')}")
        pause()
        return

    print(f"  {red(f'🔔 {len(due)} job(s) need a follow-up!')}\n")
    print(f"  {gray('These jobs were applied to 7+ days ago with no response:')}\n")

    for i, job in enumerate(due, 1):
        days = job.get("_days_since", 7)
        urgency = red("Urgent!") if days > 14 else yellow("Due")
        print(f"  {cyan(f'[{i}]')} {bold(job['title'])} at {job['company']}")
        print(f"       {gray(f'Applied {days} days ago')}  {urgency}")
        print()

    print(f"  {bold('[A]')} Generate follow-up emails for all")
    print(f"  {bold('[#]')} Pick a specific job by number")
    print(f"  {bold('[S]')} Snooze all (remind again in 3 days)")
    print(f"  {bold('[0]')} Back\n")

    choice = input(f"  {bold('→')} Action: ").strip().upper()

    if choice == "A":
        for job in due:
            _show_followup_for_job(job, jobs)

    elif choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(due):
            _show_followup_for_job(due[idx], jobs)

    elif choice == "S":
        for job in due:
            # Snooze by pretending applied 4 days ago
            job["applied_at"] = (datetime.now() - timedelta(days=4)).isoformat()
        save_jobs(jobs)
        print(green("\n  ✅ Snoozed. We'll remind you again in 3 days."))
        pause()


def _show_followup_for_job(job: dict, jobs: list):
    """Show follow-up email for one job and handle actions."""
    clear()
    header(f"Follow-Up — {job['title']} @ {job['company']}")

    print(f"  {gray('🤖 Writing follow-up email...')}\n")
    email = generate_followup_email(job)

    print(f"  {bold('📧 Suggested Follow-Up Email:')}\n")
    print(f"  {bold('Subject:')} Following up on {job['title']} Application\n")
    print(f"  {gray('─' * 55)}")
    for line in email.split("\n"):
        print(f"  {line}")
    print(f"  {gray('─' * 55)}")

    if job.get("url"):
        print(f"\n  {gray('Job URL:')} {job['url']}")

    print(f"\n  {bold('[M]')} Mark as followed up   {bold('[R]')} Regenerate   {bold('[Enter]')} Skip\n")
    action = input(f"  {bold('→')} Action: ").strip().upper()

    if action == "M":
        for i, j in enumerate(jobs):
            if j["id"] == job["id"]:
                jobs[i]["followup_sent"] = True
                jobs[i]["followup_at"]   = datetime.now().isoformat()
                break
        save_jobs(jobs)
        print(green("  ✅ Marked as followed up."))
        pause()

    elif action == "R":
        _show_followup_for_job(job, jobs)


# ─── Daily Check (for monitor mode) ───────────────────────────────────────────
def check_and_print_reminders():
    """Called by the monitor to print any due reminders to console."""
    jobs = load_jobs()
    due  = get_followup_due(jobs, days=7)
    if due:
        print(f"\n{C.YELLOW}🔔 FOLLOW-UP REMINDER: {len(due)} job(s) need a follow-up!{C.RESET}")
        for job in due:
            print(f"   • {job['title']} at {job['company']} — applied {job.get('_days_since', 7)} days ago")
        print(f"{C.YELLOW}   Run 'python reminders.py' to generate follow-up emails.{C.RESET}\n")


if __name__ == "__main__":
    reminders_menu()
