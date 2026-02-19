"""
job_manager.py — View & Manage Your Saved Jobs
================================================
• Browse all saved jobs in a table
• Filter by status, company, location, source
• Mark jobs as: Applied / Saved / Rejected / Interview / Offer
• Add personal notes to any job
• Export to CSV
• Delete jobs you don't want

Run:  python job_manager.py
"""

import json
import os
import csv
from datetime import datetime
from ai_tools import ai_tools_menu
from reminders import reminders_menu

SAVED_JOBS_FILE = "saved_jobs.json"
EXPORT_FILE     = "jobs_export.csv"

# ─── Statuses ──────────────────────────────────────────────────────────────────
STATUSES = {
    "1": ("💾", "Saved",      "\033[96m"),   # cyan
    "2": ("📤", "Applied",    "\033[94m"),   # blue
    "3": ("💬", "Interview",  "\033[93m"),   # yellow
    "4": ("🎉", "Offer",      "\033[92m"),   # green
    "5": ("❌", "Rejected",   "\033[91m"),   # red
    "6": ("👻", "No Response","\033[90m"),   # gray
}

# ─── Colors ────────────────────────────────────────────────────────────────────
class C:
    BOLD   = "\033[1m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    GRAY   = "\033[90m"
    WHITE  = "\033[97m"
    RESET  = "\033[0m"

def bold(t):   return f"{C.BOLD}{t}{C.RESET}"
def blue(t):   return f"{C.BLUE}{t}{C.RESET}"
def cyan(t):   return f"{C.CYAN}{t}{C.RESET}"
def green(t):  return f"{C.GREEN}{t}{C.RESET}"
def yellow(t): return f"{C.YELLOW}{t}{C.RESET}"
def gray(t):   return f"{C.GRAY}{t}{C.RESET}"
def red(t):    return f"{C.RED}{t}{C.RESET}"

def clear(): os.system("cls" if os.name == "nt" else "clear")

def header(sub=""):
    print(f"\n{bold(blue('═' * 62))}")
    print(f"  {bold(cyan('📋 JOB MANAGER'))}  {gray(sub)}")
    print(f"{bold(blue('═' * 62))}\n")

def pause():
    input(f"\n  {gray('Press Enter to continue...')}")


# ─── Data Layer ────────────────────────────────────────────────────────────────
def load_jobs() -> list:
    if not os.path.exists(SAVED_JOBS_FILE):
        return []
    try:
        with open(SAVED_JOBS_FILE, "r") as f:
            jobs = json.load(f)
        # Ensure all jobs have required fields
        for i, job in enumerate(jobs):
            job.setdefault("id", i + 1)
            job.setdefault("status", "Saved")
            job.setdefault("notes", "")
            job.setdefault("saved_at", "")
            job.setdefault("applied_at", "")
            job.setdefault("title", "Unknown Role")
            job.setdefault("company", "Unknown Company")
            job.setdefault("location", "")
            job.setdefault("url", "")
            job.setdefault("source", "")
        return jobs
    except Exception as e:
        print(red(f"  Error loading jobs: {e}"))
        return []

def save_jobs(jobs: list):
    # Re-assign sequential IDs
    for i, job in enumerate(jobs):
        job["id"] = i + 1
    with open(SAVED_JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)

def status_label(status: str) -> str:
    for key, (icon, label, color) in STATUSES.items():
        if label == status:
            return f"{color}{icon} {label}{C.RESET}"
    return gray("💾 Saved")


# ─── Display Jobs Table ────────────────────────────────────────────────────────
def display_jobs(jobs: list, title: str = "All Jobs"):
    clear()
    header(title)

    if not jobs:
        print(f"  {yellow('No jobs found.')}\n")
        print(f"  {gray('Run the agent first to find and save jobs.')}")
        return

    # Column widths
    W_ID    = 4
    W_ROLE  = 26
    W_CO    = 22
    W_LOC   = 16
    W_STAT  = 18
    W_DATE  = 11

    # Header row
    h = (
        f"  {bold(gray('#'.ljust(W_ID)))}"
        f"  {bold(gray('Role'.ljust(W_ROLE)))}"
        f"  {bold(gray('Company'.ljust(W_CO)))}"
        f"  {bold(gray('Location'.ljust(W_LOC)))}"
        f"  {bold(gray('Status'.ljust(W_STAT)))}"
        f"  {bold(gray('Saved'.ljust(W_DATE)))}"
    )
    print(h)
    print(f"  {gray('─' * 100)}")

    for job in jobs:
        job_id   = str(job["id"]).ljust(W_ID)
        role     = job["title"][:W_ROLE].ljust(W_ROLE)
        company  = job["company"][:W_CO].ljust(W_CO)
        location = (job["location"] or "Remote")[:W_LOC].ljust(W_LOC)
        stat     = status_label(job.get("status", "Saved"))
        date     = (job.get("saved_at") or "")[:10]

        note_icon = f" {yellow('✎')}" if job.get("notes") else ""

        print(
            f"  {cyan(job_id)}"
            f"  {white_or_gray(role, job)}"
            f"  {gray(company)}"
            f"  {gray(location)}"
            f"  {stat}"
            f"  {gray(date)}{note_icon}"
        )

    print(f"\n  {gray(f'Total: {len(jobs)} job(s)')}")

def white_or_gray(text, job):
    """Make active jobs bright, rejected/no-response dim."""
    dim = job.get("status") in ("Rejected", "No Response")
    return gray(text) if dim else bold(text)


# ─── Stats Dashboard ───────────────────────────────────────────────────────────
def show_stats(jobs: list):
    clear()
    header("Dashboard")

    if not jobs:
        print(yellow("  No jobs saved yet."))
        pause()
        return

    counts = {}
    for job in jobs:
        s = job.get("status", "Saved")
        counts[s] = counts.get(s, 0) + 1

    total = len(jobs)

    print(f"  {bold('📊 Your Job Search Stats')}\n")
    print(f"  {bold('Total saved:')}  {cyan(str(total))}\n")

    bar_width = 30
    for key, (icon, label, color) in STATUSES.items():
        count = counts.get(label, 0)
        pct   = count / total if total else 0
        bar   = "█" * int(pct * bar_width) + "░" * (bar_width - int(pct * bar_width))
        print(f"  {color}{icon} {label.ljust(14)} {bar}  {count}{C.RESET}")

    # Sources breakdown
    sources = {}
    for job in jobs:
        s = job.get("source", "Unknown")
        sources[s] = sources.get(s, 0) + 1

    print(f"\n  {bold('📡 Sources:')}")
    for src, cnt in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"    {gray('•')} {cyan(src.ljust(25))} {cnt} job(s)")

    # Companies
    companies = {}
    for job in jobs:
        c = job.get("company", "Unknown")
        companies[c] = companies.get(c, 0) + 1

    if companies:
        top = sorted(companies.items(), key=lambda x: -x[1])[:5]
        print(f"\n  {bold('🏢 Top Companies:')}")
        for co, cnt in top:
            print(f"    {gray('•')} {cyan(co.ljust(25))} {cnt} role(s)")

    pause()


# ─── View Single Job ───────────────────────────────────────────────────────────
def view_job(job: dict):
    clear()
    header(f"Job #{job['id']}")

    print(f"  {bold('Title:')}      {cyan(job['title'])}")
    print(f"  {bold('Company:')}    {job['company']}")
    print(f"  {bold('Location:')}   {job.get('location') or 'Not specified'}")
    print(f"  {bold('Source:')}     {gray(job.get('source', ''))}")
    print(f"  {bold('Status:')}     {status_label(job.get('status', 'Saved'))}")
    print(f"  {bold('Saved At:')}   {gray((job.get('saved_at') or '')[:19])}")

    if job.get("applied_at"):
        print(f"  {bold('Applied At:')} {gray(job['applied_at'][:19])}")

    if job.get("url"):
        print(f"\n  {bold('Link:')}  {blue(job['url'])}")

    if job.get("notes"):
        print(f"\n  {bold('Notes:')}")
        print(f"  {gray(job['notes'])}")

    print(f"\n  {gray('─' * 55)}")
    print(f"  {bold('[S]')} Change status   {bold('[N]')} Edit notes   {bold('[D]')} Delete   {bold('[Enter]')} Back")
    print(f"  {bold('[A]')} AI Tools (score/tailor/cover letter/interview prep)")
    print()

    action = input(f"  {bold('→')} Action: ").strip().upper()
    return action, job


# ─── Filter Jobs ───────────────────────────────────────────────────────────────
def filter_menu(jobs: list) -> list:
    clear()
    header("Filter Jobs")

    print(f"  {bold('Filter by Status:')}\n")
    print(f"    {cyan('[0]')} Show all")
    for key, (icon, label, color) in STATUSES.items():
        print(f"    {cyan(f'[{key}]')} {color}{icon} {label}{C.RESET}")

    print()
    choice = input(f"  {bold('→')} Status filter (0-6): ").strip()

    if choice == "0" or not choice:
        filtered = jobs
    elif choice in STATUSES:
        _, label, _ = STATUSES[choice]
        filtered = [j for j in jobs if j.get("status", "Saved") == label]
    else:
        filtered = jobs

    # Optional keyword filter
    print()
    kw = input(f"  {bold('→')} Filter by keyword (company/role/location, or Enter to skip): ").strip().lower()
    if kw:
        filtered = [
            j for j in filtered
            if kw in j.get("title", "").lower()
            or kw in j.get("company", "").lower()
            or kw in j.get("location", "").lower()
            or kw in j.get("notes", "").lower()
        ]

    return filtered


# ─── Update Status ─────────────────────────────────────────────────────────────
def update_status(job: dict, jobs: list) -> list:
    clear()
    header(f"Update Status — {job['title']} @ {job['company']}")

    print(f"  Current: {status_label(job.get('status', 'Saved'))}\n")
    print(f"  {bold('New status:')}\n")
    for key, (icon, label, color) in STATUSES.items():
        print(f"    {cyan(f'[{key}]')} {color}{icon} {label}{C.RESET}")

    print()
    choice = input(f"  {bold('→')} Choose (1-6): ").strip()

    if choice in STATUSES:
        _, label, _ = STATUSES[choice]
        old_status = job.get("status")
        job["status"] = label

        # Auto-stamp applied date
        if label == "Applied" and not job.get("applied_at"):
            job["applied_at"] = datetime.now().isoformat()

        # Find and update in main list
        for i, j in enumerate(jobs):
            if j["id"] == job["id"]:
                jobs[i] = job
                break

        save_jobs(jobs)
        print(green(f"\n  ✅ Status updated: {old_status} → {label}"))
        pause()

    return jobs


# ─── Edit Notes ────────────────────────────────────────────────────────────────
def edit_notes(job: dict, jobs: list) -> list:
    clear()
    header(f"Notes — {job['title']} @ {job['company']}")

    if job.get("notes"):
        print(f"  {bold('Current notes:')}")
        print(f"  {gray(job['notes'])}\n")
    else:
        print(f"  {gray('No notes yet.')}\n")

    print(f"  {gray('Type your notes below. Press Enter twice when done.')}")
    print(f"  {gray('(Or type CLEAR to delete notes)')}\n")

    lines = []
    while True:
        line = input("  ")
        if not line and lines:
            break
        if line.upper() == "CLEAR":
            lines = []
            break
        lines.append(line)

    job["notes"] = "\n".join(lines)
    for i, j in enumerate(jobs):
        if j["id"] == job["id"]:
            jobs[i] = job
            break

    save_jobs(jobs)
    print(green("\n  ✅ Notes saved."))
    pause()
    return jobs


# ─── Delete Job ────────────────────────────────────────────────────────────────
def delete_job(job: dict, jobs: list) -> list:
    confirm = input(f"\n  {red('Delete')} '{job['title']}' at {job['company']}? {gray('(y/N)')}: ").strip().lower()
    if confirm == "y":
        jobs = [j for j in jobs if j["id"] != job["id"]]
        save_jobs(jobs)
        print(green("  ✅ Job deleted."))
        pause()
    return jobs


# ─── Export to CSV ─────────────────────────────────────────────────────────────
def export_csv(jobs: list):
    clear()
    header("Export to CSV")

    if not jobs:
        print(yellow("  No jobs to export."))
        pause()
        return

    fields = ["id", "title", "company", "location", "status", "url",
              "source", "notes", "saved_at", "applied_at"]

    with open(EXPORT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(jobs)

    print(green(f"  ✅ Exported {len(jobs)} job(s) to {bold(EXPORT_FILE)}"))
    print(f"\n  {gray('Open this file in Excel or Google Sheets.')}")
    pause()


# ─── Bulk Actions ──────────────────────────────────────────────────────────────
def bulk_actions(jobs: list) -> list:
    clear()
    header("Bulk Actions")

    print(f"  {bold('[1]')} Mark all {cyan('Saved')} jobs as {blue('Applied')}")
    print(f"  {bold('[2]')} Delete all {red('Rejected')} jobs")
    print(f"  {bold('[3]')} Delete ALL jobs {red('(⚠ cannot undo)')}")
    print(f"  {bold('[4]')} Back\n")

    choice = input(f"  {bold('→')} Action: ").strip()

    if choice == "1":
        count = 0
        for j in jobs:
            if j.get("status", "Saved") == "Saved":
                j["status"] = "Applied"
                j["applied_at"] = datetime.now().isoformat()
                count += 1
        save_jobs(jobs)
        print(green(f"\n  ✅ Marked {count} job(s) as Applied."))

    elif choice == "2":
        before = len(jobs)
        jobs = [j for j in jobs if j.get("status") != "Rejected"]
        save_jobs(jobs)
        print(green(f"\n  ✅ Deleted {before - len(jobs)} rejected job(s)."))

    elif choice == "3":
        confirm = input(red("  ⚠  Delete ALL jobs? This cannot be undone. Type YES to confirm: "))
        if confirm.strip() == "YES":
            jobs = []
            save_jobs(jobs)
            print(green("\n  ✅ All jobs deleted."))

    pause()
    return jobs


# ─── Add Job Manually ─────────────────────────────────────────────────────────
def add_job_manually(jobs: list) -> list:
    clear()
    header("Add Job Manually")

    print(f"  {gray('Add a job you found yourself (e.g. via LinkedIn, referral, etc.)')}\n")

    title   = input(f"  {bold('→')} Job title: ").strip()
    company = input(f"  {bold('→')} Company name: ").strip()
    location= input(f"  {bold('→')} Location (or 'Remote'): ").strip()
    url     = input(f"  {bold('→')} Job URL (or press Enter to skip): ").strip()
    notes   = input(f"  {bold('→')} Notes (optional): ").strip()

    if not title or not company:
        print(red("\n  Title and company are required."))
        pause()
        return jobs

    new_job = {
        "id":         len(jobs) + 1,
        "title":      title,
        "company":    company,
        "location":   location,
        "url":        url,
        "source":     "Manual Entry",
        "notes":      notes,
        "status":     "Saved",
        "saved_at":   datetime.now().isoformat(),
        "applied_at": ""
    }

    jobs.append(new_job)
    save_jobs(jobs)
    print(green(f"\n  ✅ Job saved: {title} at {company}"))
    pause()
    return jobs


# ─── Main Loop ─────────────────────────────────────────────────────────────────
def main():
    active_filter = None

    while True:
        jobs = load_jobs()
        display_jobs(active_filter if active_filter is not None else jobs,
                     f"Filtered ({len(active_filter)})" if active_filter is not None else f"All Jobs ({len(jobs)})")

        print(f"\n  {bold(blue('─── Actions ─────────────────────────────────────────'))}")
        print(f"  {bold('[#]')}  View/edit a job by its number")
        print(f"  {bold('[F]')}  Filter jobs          {bold('[A]')}  Add job manually")
        print(f"  {bold('[S]')}  Stats dashboard       {bold('[B]')}  Bulk actions")
        print(f"  {bold('[E]')}  Export to CSV         {bold('[C]')}  Clear filter")
        print(f"  {bold('[R]')}  Run job search agent  {bold('[N]')}  Follow-up Reminders")
        print(f"  {bold('[Q]')}  Quit")
        print()

        cmd = input(f"  {bold('→')} Command: ").strip().upper()

        current_jobs = active_filter if active_filter is not None else jobs

        # View by number
        if cmd.isdigit():
            job_id = int(cmd)
            match = next((j for j in jobs if j["id"] == job_id), None)
            if match:
                while True:
                    action, match = view_job(match)
                    if action == "S":
                        jobs = update_status(match, jobs)
                        active_filter = None
                    elif action == "N":
                        jobs = edit_notes(match, jobs)
                        active_filter = None
                    elif action == "D":
                        jobs = delete_job(match, jobs)
                        active_filter = None
                        break
                    elif action == "A":
                        jobs = ai_tools_menu(match, jobs)
                        active_filter = None
                    else:
                        break
            else:
                print(red(f"  Job #{job_id} not found."))
                pause()

        elif cmd == "F":
            result = filter_menu(jobs)
            active_filter = result

        elif cmd == "C":
            active_filter = None

        elif cmd == "A":
            jobs = add_job_manually(jobs)
            active_filter = None

        elif cmd == "S":
            show_stats(jobs)

        elif cmd == "B":
            jobs = bulk_actions(jobs)
            active_filter = None

        elif cmd == "E":
            export_csv(current_jobs)

        elif cmd == "R":
            print(f"\n  {green('Launching job search agent...')}\n")
            os.system("python menu.py")

        elif cmd == "N":
            reminders_menu()

        elif cmd == "Q":
            print(f"\n  {gray('Goodbye! Good luck with your job search 🍀')}\n")
            break

        else:
            print(red("  Invalid command."))


# ─── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
