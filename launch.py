"""
launch.py — Main Hub for the AI Job Search System
===================================================
Run this file to access everything:

  python launch.py

From here you can:
  → Search for new jobs (with filters)
  → Manage your saved jobs
  → Use AI tools (score, tailor, cover letter, interview prep)
  → Check follow-up reminders
  → View your stats dashboard
"""

import os
import sys
from datetime import datetime

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


def show_splash():
    clear()
    print(f"""
{bold(C.CYAN)}
  ╔══════════════════════════════════════════════════════╗
  ║           🤖  AI JOB SEARCH SYSTEM  🤖              ║
  ║       Find, Track & Land Your Next Job               ║
  ╚══════════════════════════════════════════════════════╝
{C.RESET}""")


def count_jobs_by_status() -> dict:
    """Quick stats for the dashboard."""
    import json
    try:
        if not os.path.exists("saved_jobs.json"):
            return {}
        with open("saved_jobs.json") as f:
            jobs = json.load(f)
        counts = {}
        for job in jobs:
            s = job.get("status", "Saved")
            counts[s] = counts.get(s, 0) + 1
        return counts
    except Exception:
        return {}


def check_reminders_quick() -> int:
    """Return count of jobs needing follow-up."""
    try:
        from reminders import load_jobs, get_followup_due
        jobs = load_jobs()
        return len(get_followup_due(jobs, days=7))
    except Exception:
        return 0


def main():
    while True:
        show_splash()

        # Quick stats
        counts  = count_jobs_by_status()
        total   = sum(counts.values())
        applied = counts.get("Applied", 0)
        interviews = counts.get("Interview", 0)
        offers  = counts.get("Offer", 0)
        due     = check_reminders_quick()

        print(f"  {bold('📊 Quick Stats')}  {gray(datetime.now().strftime('%a %b %d, %Y'))}")
        print(f"  {gray('─' * 52)}")
        print(f"  {'Saved jobs:'.ljust(18)} {cyan(str(total))}"
              f"    {'Applied:'.ljust(10)} {C.BLUE}{applied}{C.RESET}")
        print(f"  {'Interviews:'.ljust(18)} {yellow(str(interviews))}"
              f"    {'Offers:'.ljust(10)} {green(str(offers))}")

        if due:
            print(f"\n  {red(f'🔔 {due} job(s) need a follow-up email!')}")

        print(f"\n  {bold(C.BLUE + '─── Main Menu ──────────────────────────────────────' + C.RESET)}\n")
        print(f"  {bold(cyan('[1]'))}  🔍 Search for new jobs       {gray('(job boards + Maps + startups)')}")
        print(f"  {bold(cyan('[2]'))}  📋 Manage saved jobs          {gray('(view, filter, update status)')}")
        print(f"  {bold(cyan('[3]'))}  🤖 AI Career Tools            {gray('(score, tailor, cover letter, prep)')}")
        print(f"  {bold(cyan('[4]'))}  🔔 Follow-up Reminders        " + (red(f'({due} due!)') if due else gray('(check who to follow up with)')))
        print(f"  {bold(cyan('[5]'))}  📊 Stats Dashboard")
        print(f"  {bold(cyan('[6]'))}  ⚙️  Setup (API keys, resume)")
        print(f"  {bold(cyan('[Q]'))}  Exit\n")

        choice = input(f"  {bold('→')} Choose: ").strip().upper()

        if choice == "1":
            print(f"\n  {green('Launching job search...')}")
            os.system("python menu.py")

        elif choice == "2":
            from job_manager import main as manager_main
            manager_main()

        elif choice == "3":
            ai_tools_hub()

        elif choice == "4":
            from reminders import reminders_menu
            reminders_menu()

        elif choice == "5":
            stats_hub()

        elif choice == "6":
            setup_hub()

        elif choice == "Q":
            print(f"\n  {gray('Good luck! 🍀  You got this.\n')}")
            sys.exit(0)

        else:
            print(red("  Invalid choice."))


# ─── AI Tools Hub ──────────────────────────────────────────────────────────────
def ai_tools_hub():
    """Pick a job then run AI tools on it."""
    import json
    from ai_tools import ai_tools_menu

    clear()
    print(f"\n{bold(C.CYAN + '  🤖 AI Career Tools' + C.RESET)}\n")

    try:
        with open("saved_jobs.json") as f:
            jobs = json.load(f)
    except Exception:
        print(yellow("  No saved jobs yet. Search for jobs first."))
        input(gray("\n  Press Enter to continue..."))
        return

    if not jobs:
        print(yellow("  No saved jobs yet."))
        input(gray("\n  Press Enter to continue..."))
        return

    print(f"  {gray('Pick a job to use AI tools on:')}\n")
    for job in jobs[:15]:
        score = f"  {green(str(job.get('match_score')) + '%')}" if job.get("match_score") else ""
        jid = job["id"]
        print(f"    {cyan(f'[{jid}]')} {bold(job['title'])} at {job['company']}{score}")

    print()
    choice = input(f"  {bold('→')} Enter job number: ").strip()

    if choice.isdigit():
        job_id = int(choice)
        match = next((j for j in jobs if j["id"] == job_id), None)
        if match:
            jobs = ai_tools_menu(match, jobs)
        else:
            print(red(f"  Job #{job_id} not found."))
            input(gray("\n  Press Enter to continue..."))


# ─── Stats Hub ─────────────────────────────────────────────────────────────────
def stats_hub():
    from job_manager import show_stats, load_jobs
    show_stats(load_jobs())


# ─── Setup Hub ─────────────────────────────────────────────────────────────────
def setup_hub():
    clear()
    print(f"\n{bold(cyan('  ⚙️  Setup & Configuration'))}\n")
    print(f"  {bold('[1]')} Update my resume")
    print(f"  {bold('[2]')} View/edit config.py (API keys)")
    print(f"  {bold('[3]')} Check API key status")
    print(f"  {bold('[0]')} Back\n")

    choice = input(f"  {bold('→')} Choose: ").strip()

    if choice == "1":
        clear()
        print(f"\n  {bold(cyan('📄 Update Resume'))}\n")
        print(f"  {gray('Paste your resume below. Press Enter twice when done.')}\n")
        lines = []
        while True:
            line = input("  ")
            if not line and lines:
                break
            lines.append(line)
        with open("my_resume.txt", "w") as f:
            f.write("\n".join(lines))
        print(green("\n  ✅ Resume saved to my_resume.txt"))

    elif choice == "2":
        editor = os.environ.get("EDITOR", "nano")
        os.system(f"{editor} config.py")

    elif choice == "3":
        _check_api_keys()

    input(f"\n  {gray('Press Enter to continue...')}")


def _check_api_keys():
    print(f"\n  {bold('API Key Status:')}\n")
    import os as _os

    # Anthropic
    ak = _os.environ.get("ANTHROPIC_API_KEY", "")
    if ak and ak.startswith("sk-"):
        print(f"  {green('✅')} Anthropic (Claude AI)   — Connected")
    else:
        print(f"  {red('❌')} Anthropic (Claude AI)   — Missing (set ANTHROPIC_API_KEY env var)")

    # Adzuna
    try:
        from config import ADZUNA_APP_ID, ADZUNA_APP_KEY
        if ADZUNA_APP_ID != "YOUR_ADZUNA_APP_ID":
            print(f"  {green('✅')} Adzuna Job Board       — Configured")
        else:
            print(f"  {yellow('⚠️ ')} Adzuna Job Board       — Not configured (edit config.py)")
    except Exception:
        print(f"  {red('❌')} Adzuna Job Board       — Error reading config.py")

    # Google Maps
    try:
        from config import GOOGLE_MAPS_API_KEY
        if GOOGLE_MAPS_API_KEY != "YOUR_GOOGLE_MAPS_API_KEY":
            print(f"  {green('✅')} Google Maps/Places     — Configured")
        else:
            print(f"  {yellow('⚠️ ')} Google Maps/Places     — Not configured (optional)")
    except Exception:
        print(f"  {red('❌')} Google Maps/Places     — Error reading config.py")

    # Resume
    if os.path.exists("my_resume.txt"):
        size = os.path.getsize("my_resume.txt")
        print(f"  {green('✅')} Resume file            — Found ({size} bytes)")
    else:
        print(f"  {yellow('⚠️ ')} Resume file            — Not set up (needed for AI tools)")

    # Free sources (no keys needed)
    print(f"  {green('✅')} RemoteOK               — Ready (no key needed)")
    print(f"  {green('✅')} Hacker News Jobs       — Ready (no key needed)")
    print(f"  {green('✅')} Indeed RSS             — Ready (no key needed)")


if __name__ == "__main__":
    main()
