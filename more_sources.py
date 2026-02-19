"""
more_sources.py — Extra Job Board Sources
==========================================
• Wellfound (Y Combinator / AngelList) — startup-focused
• RemoteOK — remote-only jobs
• Indeed — via scraping (no API needed)
• GitHub Jobs feed (open source / dev roles)
• Hacker News "Who is Hiring" thread
"""

import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ─── 1. Wellfound / AngelList (Startup Jobs) ──────────────────────────────────
def search_wellfound(keywords: str, location: str = "", max_results: int = 15) -> str:
    """
    Scrape Wellfound (formerly AngelList Talent) for startup jobs.
    These are Y Combinator and venture-backed startups — very early postings.
    """
    try:
        # Wellfound uses a structured URL for searches
        loc_slug = location.lower().replace(" ", "-").replace(",", "") if location else "remote"
        role_slug = keywords.lower().replace(" ", "-")

        urls_to_try = [
            f"https://wellfound.com/role/r/{role_slug}",
            f"https://wellfound.com/jobs?q={keywords.replace(' ', '+')}&l={location.replace(' ', '+')}",
        ]

        for url in urls_to_try:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=12)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")

                    # Extract job cards
                    cards = soup.find_all(class_=lambda c: c and "job" in c.lower(), limit=30)
                    jobs = []

                    for card in cards:
                        text = card.get_text(separator=" | ", strip=True)
                        if 30 < len(text) < 500:
                            jobs.append(text)

                    if jobs:
                        out = [f"🚀 Wellfound Startup Jobs for '{keywords}':\n"]
                        for i, j in enumerate(jobs[:max_results], 1):
                            out.append(f"{i}. {j}")
                        out.append(f"\n🔗 View more: {url}")
                        return "\n".join(out)
            except Exception:
                continue

        # Fallback: return direct search URL
        search_url = f"https://wellfound.com/jobs?q={keywords.replace(' ', '+')}"
        return (
            f"Wellfound search ready. Could not auto-scrape (they use heavy JS).\n"
            f"👉 Open this URL to find startup jobs: {search_url}\n"
            f"Wellfound specialises in Y Combinator and funded startups — great for early-stage roles."
        )

    except Exception as e:
        return f"Wellfound search error: {str(e)}"


# ─── 2. RemoteOK (Remote-Only Jobs) ──────────────────────────────────────────
def search_remoteok(keywords: str, max_results: int = 15) -> str:
    """
    Search RemoteOK.com — remote-only tech jobs, updated frequently.
    They have a public JSON API.
    """
    try:
        # RemoteOK has a free public API
        resp = requests.get(
            "https://remoteok.com/api",
            headers={**HEADERS, "Accept": "application/json"},
            timeout=12
        )
        resp.raise_for_status()
        data = resp.json()

        # First item is a legal notice, skip it
        jobs = [j for j in data if isinstance(j, dict) and j.get("position")]

        # Filter by keywords
        kw_lower = keywords.lower().split()
        matched = []
        for job in jobs:
            text = f"{job.get('position', '')} {job.get('description', '')} {' '.join(job.get('tags', []))}".lower()
            if any(kw in text for kw in kw_lower):
                matched.append(job)

        if not matched:
            # Return most recent if no keyword match
            matched = jobs[:max_results]

        out = [f"🌐 RemoteOK Jobs for '{keywords}' (remote only):\n"]
        for i, job in enumerate(matched[:max_results], 1):
            posted = job.get("date", "")[:10] if job.get("date") else "Recently"
            tags   = ", ".join(job.get("tags", [])[:4])
            out.append(
                f"{i}. 📌 {job.get('position', 'N/A')}\n"
                f"   Company: {job.get('company', 'N/A')}\n"
                f"   Tags:    {tags}\n"
                f"   Posted:  {posted}\n"
                f"   Link:    https://remoteok.com/remote-jobs/{job.get('id', '')}\n"
            )

        out.append(f"🔗 Browse more: https://remoteok.com/?q={keywords.replace(' ', '+')}")
        return "\n".join(out)

    except Exception as e:
        return f"RemoteOK error: {str(e)}\nBrowse manually: https://remoteok.com"


# ─── 3. Indeed (via RSS feed) ─────────────────────────────────────────────────
def search_indeed(keywords: str, location: str = "", max_results: int = 15) -> str:
    """
    Search Indeed via their public RSS feed — no API key needed.
    Returns freshest postings sorted by date.
    """
    try:
        params = {
            "q":   keywords,
            "l":   location,
            "sort": "date",
            "limit": max_results,
        }
        query  = "&".join(f"{k}={v}" for k, v in params.items() if v)
        rss_url = f"https://www.indeed.com/rss?{query}"

        resp = requests.get(rss_url, headers=HEADERS, timeout=12)
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        channel = root.find("channel")
        items   = channel.findall("item") if channel else []

        if not items:
            search_url = f"https://www.indeed.com/jobs?q={keywords.replace(' ', '+')}&l={location.replace(' ', '+')}&sort=date"
            return f"Indeed RSS returned no results.\n👉 Try directly: {search_url}"

        out = [f"📋 Indeed Jobs for '{keywords}'" + (f" in '{location}'" if location else "") + ":\n"]
        for i, item in enumerate(items[:max_results], 1):
            title   = item.findtext("title", "N/A")
            link    = item.findtext("link", "")
            pub     = item.findtext("pubDate", "")[:16] if item.findtext("pubDate") else ""
            desc    = item.findtext("description", "")
            # Strip HTML from description
            if desc:
                soup = BeautifulSoup(desc, "html.parser")
                desc = soup.get_text(separator=" ", strip=True)[:150]

            out.append(
                f"{i}. 📌 {title}\n"
                f"   Posted: {pub}\n"
                f"   {gray_plain(desc)}\n"
                f"   Link:   {link}\n"
            )

        search_url = f"https://www.indeed.com/jobs?q={keywords.replace(' ', '+')}&sort=date"
        out.append(f"🔗 View all: {search_url}")
        return "\n".join(out)

    except Exception as e:
        search_url = f"https://www.indeed.com/jobs?q={keywords.replace(' ', '+')}&sort=date"
        return f"Indeed RSS error: {str(e)}\n👉 Search directly: {search_url}"

def gray_plain(t): return t  # Plain text version for file output


# ─── 4. Hacker News "Who Is Hiring" ──────────────────────────────────────────
def search_hn_hiring(keywords: str, max_results: int = 15) -> str:
    """
    Search the Hacker News monthly 'Who Is Hiring?' thread.
    This is where YC founders and startups post jobs directly — very fresh.
    Uses the official HN Algolia search API.
    """
    try:
        # Search HN for "Who is Hiring" posts
        hn_url = "https://hn.algolia.com/api/v1/search_by_date"
        resp = requests.get(hn_url, params={
            "query":       f"who is hiring {keywords}",
            "tags":        "comment,story",
            "numericFilters": f"created_at_i>{int((datetime.now() - timedelta(days=60)).timestamp())}",
            "hitsPerPage": max_results
        }, timeout=10)

        data  = resp.json()
        hits  = data.get("hits", [])

        # Filter to actual job posts
        job_hits = [
            h for h in hits
            if any(kw.lower() in (h.get("comment_text") or h.get("title") or "").lower()
                   for kw in keywords.split())
            and len(h.get("comment_text") or "") > 100
        ]

        if not job_hits:
            return (
                f"No recent HN hiring posts found for '{keywords}'.\n"
                f"👉 Check manually: https://news.ycombinator.com/jobs\n"
                f"👉 Or search: https://hn.algolia.com/?q={keywords.replace(' ', '+')}&type=job"
            )

        out = [f"🟠 Hacker News Jobs for '{keywords}':\n"]
        for i, hit in enumerate(job_hits[:max_results], 1):
            text = (hit.get("comment_text") or hit.get("title") or "")[:300]
            # Clean HTML
            soup = BeautifulSoup(text, "html.parser")
            text = soup.get_text(separator=" ", strip=True)

            created = hit.get("created_at", "")[:10]
            hn_link  = f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"

            out.append(
                f"{i}. {text[:200]}...\n"
                f"   Posted: {created}  |  Link: {hn_link}\n"
            )

        out.append(f"\n🔗 Browse HN jobs: https://news.ycombinator.com/jobs")
        return "\n".join(out)

    except Exception as e:
        return (
            f"HN search error: {str(e)}\n"
            f"👉 Browse HN jobs: https://news.ycombinator.com/jobs"
        )


# ─── 5. Glassdoor (URL builder) ───────────────────────────────────────────────
def search_glassdoor(keywords: str, location: str = "") -> str:
    """
    Glassdoor doesn't allow scraping, but we build the search URL.
    """
    kw  = keywords.replace(" ", "-").lower()
    loc = location.replace(" ", "-").lower() if location else ""
    url = f"https://www.glassdoor.com/Job/{loc + '-' if loc else ''}{kw}-jobs-SRCH_KO0,{len(kw)}.htm?sortBy=date_desc"
    return (
        f"Glassdoor (sorted by newest):\n"
        f"👉 {url}\n\n"
        f"Tip: Filter by 'Posted this week' after opening the link for the freshest jobs."
    )


# ─── All Sources Combined ─────────────────────────────────────────────────────
def search_all_sources(keywords: str, location: str = "", max_results: int = 10) -> str:
    """Run all sources and combine results."""
    results = []

    results.append("=" * 55)
    results.append(f"🌐 MULTI-SOURCE JOB SEARCH: '{keywords}'")
    results.append("=" * 55 + "\n")

    results.append("── RemoteOK ──────────────────────────────────────────")
    results.append(search_remoteok(keywords, max_results))

    results.append("\n── Indeed ────────────────────────────────────────────")
    results.append(search_indeed(keywords, location, max_results))

    results.append("\n── Wellfound Startups ────────────────────────────────")
    results.append(search_wellfound(keywords, location, max_results))

    results.append("\n── Hacker News ───────────────────────────────────────")
    results.append(search_hn_hiring(keywords, max_results))

    results.append("\n── Glassdoor (link) ──────────────────────────────────")
    results.append(search_glassdoor(keywords, location))

    return "\n".join(results)


if __name__ == "__main__":
    print(search_all_sources("Python developer", "London"))
