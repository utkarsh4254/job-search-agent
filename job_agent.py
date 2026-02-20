"""
job_agent.py — AI Job Search Agent (FREE VERSION)
==================================================
Uses Groq (Llama 3.3 70B) + Gemini fallback instead of paid Claude API.
"""

import json
import time
import schedule
from datetime import datetime

from ai_client import get_client
from tools import (
    search_job_boards, scrape_company_careers,
    find_startups_on_maps, save_job_to_file,
    load_seen_jobs, mark_job_seen
)
from more_sources import (
    search_all_sources, search_remoteok,
    search_wellfound, search_indeed, search_hn_hiring
)

TOOLS = [
    {
        "name": "search_job_boards",
        "description": "Search Adzuna job board for newly posted jobs sorted by date. Returns title, company, location, date posted, and URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords":     {"type": "string",  "description": "Job title or skills"},
                "location":     {"type": "string",  "description": "City or country"},
            },
            "required": ["keywords"]
        }
    },
    {
        "name": "scrape_company_careers",
        "description": "Scrape a company's own careers page for jobs not listed on job boards.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string", "description": "Company name"},
                "careers_url":  {"type": "string", "description": "URL of careers page"},
                "keywords":     {"type": "string", "description": "Filter by keywords (optional)"}
            },
            "required": ["company_name", "careers_url"]
        }
    },
    {
        "name": "find_startups_on_maps",
        "description": "Find small/unknown companies via Google Maps that may be hiring.",
        "input_schema": {
            "type": "object",
            "properties": {
                "industry":    {"type": "string",  "description": "e.g. software startup"},
                "location":    {"type": "string",  "description": "City or area"},
                "max_results": {"type": "integer", "description": "Max companies (default 10)"}
            },
            "required": ["industry", "location"]
        }
    },
    {
        "name": "search_more_sources",
        "description": "Search RemoteOK, Wellfound (YC startups), Indeed, or Hacker News hiring posts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {"type": "string", "description": "Job title or skills"},
                "location": {"type": "string", "description": "City or blank for remote"},
                "source": {
                    "type": "string",
                    "description": "Which source to use",
                    "enum": ["all", "remoteok", "wellfound", "indeed", "hackernews"]
                }
            },
            "required": ["keywords"]
        }
    },
    {
        "name": "save_job",
        "description": "Save an interesting job to the local jobs file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":    {"type": "string", "description": "Job title"},
                "company":  {"type": "string", "description": "Company name"},
                "location": {"type": "string", "description": "Job location"},
                "url":      {"type": "string", "description": "Link to the job"},
                "source":   {"type": "string", "description": "Where this job was found"},
                "notes":    {"type": "string", "description": "Extra info about this job"}
            },
            "required": ["title", "company", "source"]
        }
    }
]

SYSTEM_PROMPT = """You are an expert job search agent. Find jobs as soon as they are posted.
Strategy:
1. Search job boards for fresh postings (max_days_old=1)
2. Search Wellfound and Hacker News for startup roles
3. Find small companies via Maps that post on their own sites
4. Save every good opportunity using save_job
5. Give a clear summary of what you found
Be thorough. Use multiple tools. Always sort by newest first."""


def execute_tool(name: str, inputs: dict) -> str:
    try:
        if name == "search_job_boards":
            return search_job_boards(inputs["keywords"], inputs.get("location", ""), 1)
        elif name == "scrape_company_careers":
            return scrape_company_careers(inputs["company_name"], inputs["careers_url"], inputs.get("keywords", ""))
        elif name == "find_startups_on_maps":
            return find_startups_on_maps(inputs["industry"], inputs["location"], inputs.get("max_results", 10))
        elif name == "search_more_sources":
            src = inputs.get("source", "all")
            kw  = inputs["keywords"]
            loc = inputs.get("location", "")
            if src == "remoteok":     return search_remoteok(kw)
            elif src == "wellfound":  return search_wellfound(kw, loc)
            elif src == "indeed":     return search_indeed(kw, loc)
            elif src == "hackernews": return search_hn_hiring(kw)
            else:                     return search_all_sources(kw, loc)
        elif name == "save_job":
            return save_job_to_file(inputs)
        else:
            return f"Unknown tool: {name}"
    except Exception as e:
        return f"Tool error in {name}: {str(e)}"


def run_agent(goal: str, verbose: bool = True) -> str:
    if verbose:
        print(f"\n{'='*60}\n🎯 GOAL: {goal.strip()[:200]}\n{'='*60}\n")

    ai = get_client()
    if verbose:
        print(f"🤖 AI: {ai.status()}\n")

    messages  = [{"role": "user", "content": goal}]
    max_turns = 20

    for turn in range(max_turns):
        response   = ai.chat(messages, TOOLS, SYSTEM_PROMPT)
        stop       = response["stop_reason"]
        text       = response.get("content", "")
        tool_calls = response.get("tool_calls", [])

        if stop == "tool_use":
            assistant_blocks = []
            if text:
                assistant_blocks.append({"type": "text", "text": text})
            for tc in tool_calls:
                assistant_blocks.append({"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc["input"]})
            messages.append({"role": "assistant", "content": assistant_blocks})

            tool_results = []
            for tc in tool_calls:
                if verbose:
                    print(f"🔧 [{tc['name']}] {json.dumps(tc['input'])[:120]}")
                result = execute_tool(tc["name"], tc["input"])
                if verbose:
                    print(f"   → {result[:250]}{'...' if len(result) > 250 else ''}\n")
                tool_results.append({"type": "tool_result", "tool_use_id": tc["id"], "content": result})
            messages.append({"role": "user", "content": tool_results})
        else:
            if verbose and text:
                print(f"\n✅ SUMMARY:\n{text}")
            return text

    print("⚠️  Max turns reached.")
    return "Search complete."


def monitor_jobs(search_config: dict):
    keywords = search_config.get("keywords", "software engineer")
    location = search_config.get("location", "")
    interval = search_config.get("check_every_minutes", 30)

    print(f"\n🚨 MONITOR STARTED — '{keywords}' every {interval} min\n")

    def check():
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] 🔍 Checking...")
        goal = f"Find brand new '{keywords}' jobs{' in ' + location if location else ''} posted in the last hour. Search all sources. Save any found."
        run_agent(goal, verbose=False)
        print(f"[{now}] ✅ Done. Next in {interval} min.")

    check()
    schedule.every(interval).minutes.do(check)
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    print("\n🤖 JOB SEARCH AGENT (Free Edition)\n" + "="*40)
    print("1. Single search\n2. Monitor mode\n")
    choice = input("Choose (1 or 2): ").strip()
    if choice == "1":
        goal = input("What jobs are you looking for? ").strip() or "Find software engineer jobs posted today."
        run_agent(goal)
    elif choice == "2":
        kw  = input("Keywords: ").strip() or "software engineer"
        loc = input("Location (blank=anywhere): ").strip()
        ivl = input("Check every X minutes (default 30): ").strip()
        monitor_jobs({"keywords": kw, "location": loc, "check_every_minutes": int(ivl) if ivl.isdigit() else 30})
    else:
        run_agent("Find software engineer jobs posted today across all sources.")
