"""
menu.py — Interactive Filter Menu for Job Search Agent
=======================================================
Run this file to set your job search filters and launch the agent.
"""

import json
import os
from datetime import datetime


# ─── Color Helpers ─────────────────────────────────────────────────────────────
class C:
    BOLD   = "\033[1m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    GRAY   = "\033[90m"
    RESET  = "\033[0m"

def bold(t):   return f"{C.BOLD}{t}{C.RESET}"
def blue(t):   return f"{C.BLUE}{t}{C.RESET}"
def cyan(t):   return f"{C.CYAN}{t}{C.RESET}"
def green(t):  return f"{C.GREEN}{t}{C.RESET}"
def yellow(t): return f"{C.YELLOW}{t}{C.RESET}"
def gray(t):   return f"{C.GRAY}{t}{C.RESET}"
def red(t):    return f"{C.RED}{t}{C.RESET}"


# ─── Menu Utilities ────────────────────────────────────────────────────────────
def clear():
    os.system("cls" if os.name == "nt" else "clear")

def header(title: str):
    print(f"\n{bold(blue('═' * 55))}")
    print(f"  {bold(cyan('🤖 AI JOB SEARCH AGENT'))}   {gray(title)}")
    print(f"{bold(blue('═' * 55))}\n")

def section(title: str):
    print(f"\n  {bold(yellow('▸ ' + title))}")
    print(f"  {gray('─' * 48)}")

def choose(prompt: str, options: list, multi: bool = False, default: int = None) -> list | str:
    """
    Display a numbered list of options and return the user's choice(s).
    multi=True allows selecting multiple with comma-separated input.
    """
    for i, opt in enumerate(options, 1):
        marker = green(f"[{i}]")
        default_tag = gray(" (default)") if default == i else ""
        print(f"    {marker} {opt}{default_tag}")
    print()

    while True:
        if multi:
            raw = input(f"  {bold('→')} {prompt} (e.g. 1,3 or press Enter to skip): ").strip()
        else:
            raw = input(f"  {bold('→')} {prompt} (Enter for default): ").strip()

        if not raw:
            if default:
                return [options[default - 1]] if multi else options[default - 1]
            return [] if multi else None

        try:
            indices = [int(x.strip()) for x in raw.split(",")]
            selected = [options[i - 1] for i in indices if 1 <= i <= len(options)]
            if selected:
                return selected if multi else selected[0]
        except (ValueError, IndexError):
            pass
        print(red("    ⚠  Invalid input. Try again."))

def text_input(prompt: str, default: str = "") -> str:
    val = input(f"  {bold('→')} {prompt}{gray(f' [{default}]') if default else ''}: ").strip()
    return val if val else default

def yesno(prompt: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    val = input(f"  {bold('→')} {prompt} {gray(f'({d})')}: ").strip().lower()
    if not val:
        return default
    return val.startswith("y")


# ─── Profile Save/Load ─────────────────────────────────────────────────────────
PROFILE_FILE = "search_profile.json"

def save_profile(filters: dict):
    with open(PROFILE_FILE, "w") as f:
        json.dump(filters, f, indent=2)
    print(green(f"\n  ✅ Profile saved to {PROFILE_FILE}"))

def load_profile() -> dict | None:
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r") as f:
            return json.load(f)
    return None


# ─── Summary Display ───────────────────────────────────────────────────────────
def show_summary(f: dict):
    clear()
    header("Search Summary")
    print(f"  {bold('Job Roles:')}        {cyan(', '.join(f['job_roles']))}")
    print(f"  {bold('Experience:')}       {cyan(f['experience_level'])}")
    print(f"  {bold('Job Type:')}         {cyan(', '.join(f['job_types']))}")
    print(f"  {bold('Work Mode:')}        {cyan(', '.join(f['work_modes']))}")
    print(f"  {bold('Locations:')}        {cyan(', '.join(f['locations']) if f['locations'] else 'Anywhere')}")
    salary_str = f"${f['min_salary']:,}" if f['min_salary'] else 'Any'
    print(f"  {bold('Salary (min):')}     {cyan(salary_str)}")
    print(f"  {bold('Industries:')}       {cyan(', '.join(f['industries']) if f['industries'] else 'Any')}")
    print(f"  {bold('Skills/Stack:')}     {cyan(', '.join(f['skills']) if f['skills'] else 'Not specified')}")
    print(f"  {bold('Company Size:')}     {cyan(', '.join(f['company_sizes']))}")
    print(f"  {bold('Find Startups:')}    {cyan('Yes' if f['find_startups'] else 'No')}")
    monitor_str = f"Every {f['monitor_interval']} min" if f['monitor_mode'] else 'No (single search)'
    print(f"  {bold('Monitor Mode:')}     {cyan(monitor_str)}")
    age_str = f"{f['max_days_old']} day(s)"
    print(f"  {bold('Max Job Age:')}      {cyan(age_str)}")
    print()


# ─── The Main Menu ─────────────────────────────────────────────────────────────
def run_menu() -> dict:
    clear()
    header("Welcome")

    # Check for saved profile
    saved = load_profile()
    if saved:
        print(f"  {yellow('💾 Found a saved search profile from your last session.')}")
        use_saved = yesno("  Use your saved filters?", default=True)
        if use_saved:
            show_summary(saved)
            confirm = yesno("  Start searching with these filters?", default=True)
            if confirm:
                return saved
            print()

    filters = {}

    # ── STEP 1: Job Roles ──────────────────────────────────────────────────────
    clear()
    header("Step 1 of 7 — Job Roles")
    section("What job roles are you looking for?")

    preset_roles = [
        "Software Engineer",
        "Frontend Developer",
        "Backend Developer",
        "Full Stack Developer",
        "Data Scientist",
        "Machine Learning Engineer",
        "DevOps / Platform Engineer",
        "Product Manager",
        "UX/UI Designer",
        "Data Analyst",
        "QA / Test Engineer",
        "Mobile Developer (iOS/Android)",
        "Cloud Engineer / Architect",
        "Security Engineer",
        "Technical Writer",
    ]

    print(f"  {gray('Select one or multiple roles (e.g. 1,3,5):')}\n")
    selected_roles = choose("Select job roles", preset_roles, multi=True)

    print(f"\n  {gray('Want to add custom roles not in the list?')}")
    custom = text_input("Custom roles (comma-separated, or press Enter to skip)")
    if custom:
        selected_roles += [r.strip() for r in custom.split(",") if r.strip()]

    filters["job_roles"] = selected_roles or ["Software Engineer"]

    # ── STEP 2: Experience Level ───────────────────────────────────────────────
    clear()
    header("Step 2 of 7 — Experience Level")
    section("What's your experience level?")

    levels = [
        "Internship / Student",
        "Entry Level (0–2 years)",
        "Mid Level (2–5 years)",
        "Senior Level (5–8 years)",
        "Lead / Principal (8+ years)",
        "Any level",
    ]
    filters["experience_level"] = choose("Select your level", levels, default=3)

    # ── STEP 3: Job Type ───────────────────────────────────────────────────────
    clear()
    header("Step 3 of 7 — Job Type & Work Mode")
    section("What type of job are you looking for?")

    job_types = ["Full-Time", "Part-Time", "Contract / Freelance", "Internship", "Any type"]
    filters["job_types"] = choose("Select job type(s)", job_types, multi=True, default=1)

    section("Preferred work mode:")
    work_modes = ["Remote", "Hybrid", "On-site / In-office", "Any mode"]
    filters["work_modes"] = choose("Select work mode(s)", work_modes, multi=True, default=1)

    # ── STEP 4: Location & Salary ─────────────────────────────────────────────
    clear()
    header("Step 4 of 7 — Location & Salary")
    section("Where do you want to work?")

    print(f"  {gray('Press Enter to skip for remote/anywhere jobs')}\n")
    loc_input = text_input("Enter locations (comma-separated, e.g. 'London, New York, Berlin')")
    filters["locations"] = [l.strip() for l in loc_input.split(",") if l.strip()] if loc_input else []

    section("Minimum salary requirement:")
    print(f"  {gray('Enter a number like 60000 or press Enter to skip')}\n")
    salary = text_input("Minimum annual salary (USD)", default="")
    try:
        filters["min_salary"] = int(salary.replace(",", "").replace("$", "")) if salary else None
    except ValueError:
        filters["min_salary"] = None

    # ── STEP 5: Industry & Skills ─────────────────────────────────────────────
    clear()
    header("Step 5 of 7 — Industry & Skills")
    section("Preferred industries (optional — select multiple):")

    industries = [
        "Fintech / Finance",
        "Healthcare / MedTech",
        "AI / Machine Learning",
        "E-commerce / Retail",
        "Gaming",
        "EdTech / Education",
        "SaaS / Enterprise Software",
        "Cybersecurity",
        "Climate / GreenTech",
        "Media / Entertainment",
        "Government / Public Sector",
        "Any industry",
    ]
    selected_industries = choose("Select industries", industries, multi=True)
    filters["industries"] = selected_industries if "Any industry" not in (selected_industries or []) else []

    section("Your tech skills / stack (to match job requirements):")
    print(f"  {gray('Examples: Python, React, AWS, PostgreSQL, Kubernetes, Docker')}\n")
    skills_input = text_input("Enter your skills (comma-separated, or press Enter to skip)")
    filters["skills"] = [s.strip() for s in skills_input.split(",") if s.strip()] if skills_input else []

    # ── STEP 6: Company Preferences ───────────────────────────────────────────
    clear()
    header("Step 6 of 7 — Company Preferences")
    section("What company size do you prefer?")

    sizes = [
        "Startup (1–50 employees)",
        "Small (50–200 employees)",
        "Mid-size (200–1000 employees)",
        "Large (1000+ employees)",
        "Any size",
    ]
    filters["company_sizes"] = choose("Select company size(s)", sizes, multi=True, default=5)

    section("Startup & Maps Discovery:")
    filters["find_startups"] = yesno(
        "  Search Google Maps for unlisted startups not on job boards?",
        default=True
    )

    if filters["find_startups"]:
        print(f"\n  {gray('Startup location (defaults to your job locations if blank)')}\n")
        startup_loc = text_input("Startup city/area to search (e.g. 'Austin Texas')")
        filters["startup_location"] = startup_loc or (filters["locations"][0] if filters["locations"] else "")

    # ── STEP 7: Monitoring Settings ───────────────────────────────────────────
    clear()
    header("Step 7 of 7 — Search Mode")
    section("How do you want to run the search?")

    modes = [
        "Single Search   — Run once and show results",
        "Monitor Mode    — Run continuously, alert on new jobs",
    ]
    mode_choice = choose("Select search mode", modes, default=1)
    filters["monitor_mode"] = "Monitor" in mode_choice

    if filters["monitor_mode"]:
        section("How often should the agent check for new jobs?")
        intervals = ["Every 15 minutes", "Every 30 minutes", "Every 1 hour", "Every 2 hours"]
        interval_choice = choose("Check interval", intervals, default=2)
        interval_map = {"Every 15 minutes": 15, "Every 30 minutes": 30,
                        "Every 1 hour": 60, "Every 2 hours": 120}
        filters["monitor_interval"] = interval_map.get(interval_choice, 30)
    else:
        filters["monitor_interval"] = 30

    section("How fresh should the job postings be?")
    ages = ["Last 1 hour", "Last 24 hours", "Last 3 days", "Last 7 days"]
    age_choice = choose("Max job age", ages, default=2)
    age_map = {"Last 1 hour": 0, "Last 24 hours": 1, "Last 3 days": 3, "Last 7 days": 7}
    filters["max_days_old"] = age_map.get(age_choice, 1)

    # ── Summary & Confirm ─────────────────────────────────────────────────────
    show_summary(filters)

    save_profile(filters)
    confirm = yesno("  🚀 Start searching with these filters?", default=True)
    if not confirm:
        print(yellow("\n  Returning to menu...\n"))
        return run_menu()

    return filters


# ─── Build Agent Goal from Filters ────────────────────────────────────────────
def filters_to_goal(f: dict) -> str:
    """Convert the filter dictionary into a natural language goal for the agent."""
    roles = " or ".join(f["job_roles"])
    experience = f["experience_level"]
    job_types = ", ".join(f["job_types"])
    work_modes = ", ".join(f["work_modes"])
    locations = ", ".join(f["locations"]) if f["locations"] else "anywhere (including remote)"
    skills = ", ".join(f["skills"]) if f["skills"] else ""
    industries = ", ".join(f["industries"]) if f["industries"] else "any industry"
    salary_clause = f"with minimum salary ${f['min_salary']:,}" if f.get("min_salary") else ""
    startup_clause = (
        f"Also search Google Maps for small startups and lesser-known companies "
        f"in the {f.get('startup_location', locations)} area that might be hiring "
        f"for similar roles — focus on companies with few reviews (under 100)."
        if f.get("find_startups") else ""
    )
    skills_clause = f"Especially look for jobs requiring: {skills}." if skills else ""
    days = f["max_days_old"]
    freshness = "in the last hour" if days == 0 else f"in the last {days} day(s)"

    goal = f"""
Find {experience} {roles} jobs posted {freshness}.

Filters to apply:
- Job type: {job_types}
- Work mode: {work_modes}
- Location: {locations}
- Industry: {industries}
{salary_clause}

{skills_clause}

For each search query, sort by newest first. Save the best opportunities you find.

{startup_clause}

After searching, give a clear summary of all jobs found with their company names, 
locations, links, and why each might be a good fit.
""".strip()

    return goal


# ─── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    filters = run_menu()
    goal    = filters_to_goal(filters)

    print(f"\n{bold(green('🚀 Launching agent...'))} \n")
    print(gray(f"Agent goal:\n{goal}\n"))
    print("─" * 55)

    # Import and run the agent
    from job_agent import run_agent, monitor_jobs

    if filters["monitor_mode"]:
        search_config = {
            "keywords": filters["job_roles"][0],
            "location": filters["locations"][0] if filters["locations"] else "",
            "industry": filters["industries"][0] if filters["industries"] else "tech startup",
            "check_every_minutes": filters["monitor_interval"],
        }
        monitor_jobs(search_config)
    else:
        run_agent(goal)
