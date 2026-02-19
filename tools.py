"""
tools.py — All tool implementations for the Job Search Agent
"""

import json
import os
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from config import ADZUNA_APP_ID, ADZUNA_APP_KEY, GOOGLE_MAPS_API_KEY
from more_sources import search_all_sources, search_remoteok, search_wellfound, search_indeed, search_hn_hiring

# File to store seen jobs (avoids duplicate alerts)
SEEN_JOBS_FILE = "seen_jobs.json"
SAVED_JOBS_FILE = "saved_jobs.json"


# ─── TOOL 1: Search Job Boards ─────────────────────────────────────────────────
def search_job_boards(keywords: str, location: str = "", max_days_old: int = 1) -> str:
    """
    Search Adzuna job board for fresh job postings.
    Adzuna has a free API tier: https://developer.adzuna.com/
    """
    try:
        # Build API URL — Adzuna supports many countries
        country = _detect_country(location) or "us"
        base_url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"

        params = {
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_APP_KEY,
            "results_per_page": 20,
            "what": keywords,
            "max_days_old": max_days_old,
            "sort_by": "date",           # Newest first!
            "content-type": "application/json"
        }

        if location:
            params["where"] = location

        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        jobs = data.get("results", [])
        if not jobs:
            return f"No jobs found for '{keywords}' in '{location}' in the last {max_days_old} day(s)."

        # Format results
        output = []
        output.append(f"Found {len(jobs)} jobs for '{keywords}':\n")

        for job in jobs:
            posted = job.get("created", "Unknown date")
            output.append(
                f"📌 {job.get('title', 'N/A')}\n"
                f"   Company:  {job.get('company', {}).get('display_name', 'N/A')}\n"
                f"   Location: {job.get('location', {}).get('display_name', 'N/A')}\n"
                f"   Posted:   {posted[:10] if posted != 'Unknown date' else posted}\n"
                f"   Link:     {job.get('redirect_url', 'N/A')}\n"
            )

        return "\n".join(output)

    except requests.exceptions.HTTPError as e:
        if "401" in str(e) or "403" in str(e):
            return (
                "❌ Adzuna API key error. Please check your ADZUNA_APP_ID and ADZUNA_APP_KEY in config.py\n"
                "Get free keys at: https://developer.adzuna.com/signup"
            )
        return f"Job board API error: {str(e)}"
    except Exception as e:
        return f"Error searching job boards: {str(e)}"


def _detect_country(location: str) -> str:
    """Map common locations to Adzuna country codes."""
    location_lower = location.lower()
    country_map = {
        "uk": "gb", "united kingdom": "gb", "london": "gb", "manchester": "gb",
        "us": "us", "usa": "us", "united states": "us", "new york": "us",
        "san francisco": "us", "austin": "us", "chicago": "us",
        "canada": "ca", "toronto": "ca", "vancouver": "ca",
        "australia": "au", "sydney": "au", "melbourne": "au",
        "germany": "de", "berlin": "de", "munich": "de",
        "france": "fr", "paris": "fr",
        "india": "in", "bangalore": "in", "mumbai": "in",
        "netherlands": "nl", "amsterdam": "nl",
    }
    for key, code in country_map.items():
        if key in location_lower:
            return code
    return "us"  # Default


# ─── TOOL 2: Scrape Company Career Pages ───────────────────────────────────────
def scrape_company_careers(company_name: str, careers_url: str, keywords: str = "") -> str:
    """
    Scrape a company's career page to find jobs not listed on job boards.
    Uses BeautifulSoup to extract job listings.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(careers_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove clutter
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Find job-related elements (works on most career pages)
        job_elements = (
            soup.find_all(class_=lambda c: c and any(
                word in c.lower() for word in ["job", "position", "role", "opening", "career", "posting"]
            )) or
            soup.find_all(["li", "div", "article"], limit=50)
        )

        # Extract text from these elements
        jobs_found = []
        seen_text = set()

        for el in job_elements:
            text = el.get_text(separator=" ", strip=True)

            # Filter: reasonable length and not duplicate
            if 20 < len(text) < 300 and text not in seen_text:
                # If keywords provided, only include matching items
                if keywords:
                    if any(kw.lower() in text.lower() for kw in keywords.split()):
                        jobs_found.append(text)
                        seen_text.add(text)
                else:
                    jobs_found.append(text)
                    seen_text.add(text)

            if len(jobs_found) >= 20:
                break

        if not jobs_found:
            return f"Could not extract jobs from {company_name}'s career page at {careers_url}. The page may require JavaScript or have a different structure."

        output = [f"Jobs found on {company_name}'s career page ({careers_url}):\n"]
        for i, job in enumerate(jobs_found[:15], 1):
            output.append(f"{i}. {job}")

        return "\n".join(output)

    except requests.exceptions.Timeout:
        return f"Timeout while trying to access {careers_url}"
    except requests.exceptions.HTTPError as e:
        return f"Could not access {careers_url}: HTTP {e.response.status_code}"
    except Exception as e:
        return f"Error scraping {company_name} careers page: {str(e)}"


# ─── TOOL 3: Find Startups on Google Maps ──────────────────────────────────────
def find_startups_on_maps(industry: str, location: str, max_results: int = 10) -> str:
    """
    Use Google Places API to find small/lesser-known companies and startups.
    Focuses on lower-rated or fewer-reviewed businesses (less popular = smaller).
    """
    if not GOOGLE_MAPS_API_KEY or GOOGLE_MAPS_API_KEY == "YOUR_GOOGLE_MAPS_API_KEY":
        # Graceful fallback with instructions
        return (
            "⚠️  Google Maps API key not configured.\n"
            "To enable startup discovery:\n"
            "1. Go to https://console.cloud.google.com\n"
            "2. Enable 'Places API'\n"
            "3. Create an API key\n"
            "4. Add it to config.py as GOOGLE_MAPS_API_KEY\n\n"
            f"Manual alternative: Search Google Maps for '{industry} {location}' "
            "and look for companies with few reviews (these are likely startups)."
        )

    try:
        # Step 1: Find place coordinates for the city
        geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
        geo_resp = requests.get(geocode_url, params={
            "address": location,
            "key": GOOGLE_MAPS_API_KEY
        }, timeout=10)
        geo_data = geo_resp.json()

        if not geo_data.get("results"):
            return f"Could not find location: {location}"

        loc = geo_data["results"][0]["geometry"]["location"]
        lat, lng = loc["lat"], loc["lng"]

        # Step 2: Search for companies in that area
        places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        places_resp = requests.get(places_url, params={
            "location": f"{lat},{lng}",
            "radius": 10000,          # 10km radius
            "keyword": industry,
            "type": "establishment",
            "key": GOOGLE_MAPS_API_KEY
        }, timeout=10)

        places_data = places_resp.json()
        places = places_data.get("results", [])

        if not places:
            return f"No companies found for '{industry}' in '{location}'"

        # Step 3: Filter for small/startup companies
        # Low rating count = less popular = likely smaller company
        small_companies = sorted(
            [p for p in places if p.get("user_ratings_total", 999) < 100],
            key=lambda x: x.get("user_ratings_total", 0)
        )

        # If not enough small ones, include all
        if len(small_companies) < 3:
            small_companies = places

        output = [f"🗺️  Found {len(small_companies[:max_results])} small/startup companies for '{industry}' in '{location}':\n"]

        for i, place in enumerate(small_companies[:max_results], 1):
            name = place.get("name", "Unknown")
            address = place.get("vicinity", "Address not available")
            rating = place.get("rating", "No rating")
            review_count = place.get("user_ratings_total", 0)
            place_id = place.get("place_id", "")

            # Build Google Maps link
            maps_link = f"https://maps.google.com/?place_id={place_id}"

            output.append(
                f"{i}. 🏢 {name}\n"
                f"   Address:  {address}\n"
                f"   Rating:   {rating}/5 ({review_count} reviews)\n"
                f"   Maps:     {maps_link}\n"
            )

            # Get website if available (requires Place Details API call)
            if i <= 5:  # Only for top 5 to save API calls
                try:
                    details_resp = requests.get(
                        "https://maps.googleapis.com/maps/api/place/details/json",
                        params={
                            "place_id": place_id,
                            "fields": "website",
                            "key": GOOGLE_MAPS_API_KEY
                        },
                        timeout=5
                    )
                    website = details_resp.json().get("result", {}).get("website", "")
                    if website:
                        output[-1] = output[-1].rstrip() + f"\n   Website:  {website}\n"
                    time.sleep(0.1)  # Rate limiting
                except Exception:
                    pass

        output.append("\n💡 Tip: Visit these companies' websites and look for a 'Careers' or 'Jobs' page — startups often post there first!")
        return "\n".join(output)

    except Exception as e:
        return f"Error searching Google Maps: {str(e)}"


# ─── TOOL 4: Save Jobs ─────────────────────────────────────────────────────────
def save_job_to_file(job_data: dict) -> str:
    """Save a job opportunity to the local saved jobs file."""
    try:
        jobs = []
        if os.path.exists(SAVED_JOBS_FILE):
            with open(SAVED_JOBS_FILE, "r") as f:
                jobs = json.load(f)

        job_entry = {
            "id": len(jobs) + 1,
            "saved_at": datetime.now().isoformat(),
            "title": job_data.get("title", ""),
            "company": job_data.get("company", ""),
            "location": job_data.get("location", ""),
            "url": job_data.get("url", ""),
            "source": job_data.get("source", ""),
            "notes": job_data.get("notes", ""),
            "status": "Saved",
            "applied": False,
            "applied_at": "",
            "followup_sent": False
        }

        jobs.append(job_entry)

        with open(SAVED_JOBS_FILE, "w") as f:
            json.dump(jobs, f, indent=2)

        return f"✅ Saved job: '{job_entry['title']}' at {job_entry['company']} to {SAVED_JOBS_FILE}"

    except Exception as e:
        return f"Error saving job: {str(e)}"


def load_seen_jobs() -> set:
    """Load the set of already-seen job IDs (for monitoring mode)."""
    if os.path.exists(SEEN_JOBS_FILE):
        try:
            with open(SEEN_JOBS_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def mark_job_seen(job_id: str):
    """Mark a job as seen so we don't alert on it again."""
    seen = load_seen_jobs()
    seen.add(job_id)
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen), f)
