"""
job_agent.py — AI Job Search Agent (Free Version)
Uses Groq (Llama 3.3 70B) + Gemini fallback.
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
        "description": "Search Adzuna for IT jobs posted today. Always call this first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {"type": "string", "description": "Job title or skills"},
                "location": {"type": "string", "description": "City or country"}
            },
            "required": ["keywords"]
        }
    },
    {
        "name": "search_more_sources",
        "description": "Search RemoteOK or Hacker News for extra jobs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keywords": {"type": "string", "description": "Job title or skills"},
                "location": {"type": "string", "description": "City (optional)"},
                "source": {
                    "type": "string",
                    "description": "Which source",
                    "enum": ["remoteok", "hackernews", "wellfound", "indeed", "all"]
                }
            },
            "required": ["keywords", "source"]
        }
    },
    {
        "name": "save_job",
        "description": "IMPORTANT: Save each good job you find. Call this for every job.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":    {"type": "string", "description": "Job title"},
                "company":  {"type": "string", "description": "Company name"},
                "location": {"type": "string", "description": "Job location"},
                "url":      {"type": "string", "description": "Link to the job"},
                "source":   {"type": "string", "description": "Where found"},
                "notes":    {"type": "string", "description": "Any notes"}
            },
            "required": ["title", "company", "source"]
        }
    }
]

SYSTEM_PROMPT = """You are a job search agent. Your ONLY job is:
1. Call search_job_boards once to find jobs
2. Call search_more_sources with source="remoteok" once
3. Call save_job for the TOP 5 most relevant jobs you found
4. Stop and give a short summary

RULES:
- Maximum 3 search calls total — do NOT repeat searches
- You MUST call save_job at least 3 times before finishing
- Keep it short and focused
- Do NOT search the same source twice"""


def execute_tool(name: str, inputs: dict) -> str:
    try:
        if name == "search_job_boards":
            result = search_job_boards(
                inputs["keywords"],
                inputs.get("location", ""),
                1  # Always max 1 day old
            )
            # Truncate to avoid hitting Groq's token limit
            return result[:800] + "\n[Results truncated — use save_job to save the best ones]" if len(result) > 800 else result

        elif name == "search_more_sources":
            src = inputs.get("source", "remoteok")
            kw  = inputs["keywords"]
            loc = inputs.get("location", "")
            if src == "remoteok":    result = search_remoteok(kw)
            elif src == "hackernews":result = search_hn_hiring(kw)
            elif src == "wellfound": result = search_wellfound(kw, loc)
            elif src == "indeed":    result = search_indeed(kw, loc)
            else:                    result = search_remoteok(kw)
            return result[:600] + "\n[Truncated]" if len(result) > 600 else result

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
    max_turns = 8  # Keep short to avoid rate limits
    jobs_saved = 0

    for turn in range(max_turns):
        try:
            response = ai.chat(messages, TOOLS, SYSTEM_PROMPT)
        except Exception as e:
            print(f"❌ AI error on turn {turn}: {e}")
            break

        stop       = response["stop_reason"]
        text       = response.get("content", "")
        tool_calls = response.get("tool_calls", [])

        if stop == "tool_use" and tool_calls:
            # Build assistant message
            assistant_blocks = []
            if text:
                assistant_blocks.append({"type": "text", "text": text})
            for tc in tool_calls:
                assistant_blocks.append({
                    "type": "tool_use",
                    "id":   tc["id"],
                    "name": tc["name"],
                    "input": tc["input"]
                })
            messages.append({"role": "assistant", "content": assistant_blocks})

            # Execute tools
            tool_results = []
            for tc in tool_calls:
                if verbose:
                    print(f"🔧 [{tc['name']}] {json.dumps(tc['input'])[:100]}")
                result = execute_tool(tc["name"], tc["input"])
                if tc["name"] == "save_job":
                    jobs_saved += 1
                if verbose:
                    print(f"   → {result[:200]}{'...' if len(result) > 200 else ''}\n")
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": tc["id"],
                    "content":     result
                })
            messages.append({"role": "user", "content": tool_results})

        else:
            # Agent finished
            if verbose and text:
                print(f"\n✅ DONE! Jobs saved this run: {jobs_saved}\n{text}")
            return text

    if verbose:
        print(f"⚠️  Max turns reached. Jobs saved: {jobs_saved}")
    return f"Search complete. Jobs saved: {jobs_saved}"


def monitor_jobs(search_config: dict):
    keywords = search_config.get("keywords", "software engineer")
    location = search_config.get("location", "")
    interval = search_config.get("check_every_minutes", 30)

    print(f"\n🚨 MONITOR STARTED — '{keywords}' every {interval} min\n")

    def check():
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] 🔍 Checking...")
        goal = (
            f"Find new '{keywords}' jobs"
            f"{' in ' + location if location else ''}. "
            f"Search job boards and RemoteOK. Save the top 5."
        )
        run_agent(goal, verbose=False)
        print(f"[{now}] ✅ Done. Next in {interval} min.")

    check()
    schedule.every(interval).minutes.do(check)
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    print("\n🤖 JOB SEARCH AGENT (Free)\n" + "="*40)
    print("1. Single search\n2. Monitor mode\n")
    choice = input("Choose (1 or 2): ").strip()
    if choice == "1":
        goal = input("What jobs? ").strip() or "Find IT jobs in Toronto posted today."
        run_agent(goal)
    elif choice == "2":
        kw  = input("Keywords: ").strip() or "IT jobs"
        loc = input("Location: ").strip()
        ivl = input("Every X minutes (default 30): ").strip()
        monitor_jobs({"keywords": kw, "location": loc,
                      "check_every_minutes": int(ivl) if ivl.isdigit() else 30})
    else:
        run_agent("Find IT jobs in Toronto posted today. Save the top 5.")
