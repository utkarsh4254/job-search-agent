# 🤖 AI Job Search Agent

An intelligent agent powered by Claude AI that finds jobs **as soon as they are posted**, 
scrapes company career pages, and discovers small startups via Google Maps.

---

## Features

| Feature | What it does |
|---------|-------------|
| 📋 Job Board Search | Searches Adzuna for the freshest job postings (last 1–24 hours) |
| 🌐 Career Page Scraper | Scrapes job listings directly from company websites |
| 🗺️ Startup Finder | Finds small/unknown companies via Google Maps who may be hiring |
| 🚨 Monitor Mode | Runs continuously and alerts you when new jobs appear |
| 💾 Job Saver | Saves interesting jobs to `saved_jobs.json` for review |

---

## Setup (5 minutes)

### Step 1 — Install Python packages
```bash
pip install -r requirements.txt
```

### Step 2 — Set your Anthropic key
```bash
# Mac/Linux
export ANTHROPIC_API_KEY="sk-ant-..."

# Windows
set ANTHROPIC_API_KEY=sk-ant-...
```

### Step 3 — Get your Adzuna API key (free)
1. Go to https://developer.adzuna.com/signup
2. Register a free account
3. Copy your **App ID** and **App Key**
4. Open `config.py` and paste them in

### Step 4 — (Optional) Get Google Maps API key
For startup discovery via maps:
1. Go to https://console.cloud.google.com
2. Create a project → Enable **Places API**
3. Create credentials → API Key
4. Add it to `config.py`

---

## Usage

### Mode 1: Single Search
```bash
python job_agent.py
# Choose option 1
# Type: "Find React developer jobs in London posted today"
```

### Mode 2: Continuous Monitor
```bash
python job_agent.py
# Choose option 2
# Enter: keywords, location, industry, check interval
```

The agent will check every X minutes and save new jobs to `saved_jobs.json`.

---

## Example Prompts

```
"Find Python backend developer jobs posted today in San Francisco"

"Find remote DevOps jobs posted in the last 2 hours"

"Scrape Stripe's careers page for engineering roles"

"Find small AI startups in Austin Texas that might be hiring"

"Find any software jobs posted today AND discover small fintech startups in London"
```

---

## Output Files

| File | Contents |
|------|----------|
| `saved_jobs.json` | All jobs saved by the agent |
| `seen_jobs.json` | Jobs already seen (prevents duplicate alerts) |

---

## How the Agent Thinks

```
Your Goal
   │
   ▼
Claude AI decides which tools to use
   │
   ├─► search_job_boards()     ← Adzuna API
   ├─► scrape_company_careers() ← BeautifulSoup
   ├─► find_startups_on_maps()  ← Google Places API
   └─► save_job()               ← Local JSON file
   │
   ▼
Results fed back to Claude
   │
   ▼
Claude summarizes findings & saves best opportunities
```

---

## Adding More Companies to Watch

In `config.py`, add career pages you want monitored:

```python
COMPANIES_TO_WATCH = [
    {"name": "Stripe",  "careers_url": "https://stripe.com/jobs"},
    {"name": "Linear",  "careers_url": "https://linear.app/careers"},
    {"name": "Vercel",  "careers_url": "https://vercel.com/careers"},
    {"name": "Supabase","careers_url": "https://supabase.com/careers"},
]
```

---

## Managing Your Saved Jobs

Run the job manager to view, track and export everything you've saved:

```bash
python job_manager.py
```

### What you can do in the manager

| Command | Action |
|---------|--------|
| `#` (number) | Open a job to view full details |
| `S` inside a job | Change its status |
| `N` inside a job | Add/edit personal notes |
| `D` inside a job | Delete the job |
| `F` | Filter by status or keyword |
| `A` | Add a job manually (e.g. found on LinkedIn) |
| `S` (main menu) | Stats dashboard — progress bars by status |
| `B` | Bulk actions (mark all applied, delete rejected, etc.) |
| `E` | Export to CSV (opens in Excel / Google Sheets) |
| `R` | Jump back to job search agent |

### Job Statuses

| Status | Meaning |
|--------|---------|
| 💾 Saved | Found but not yet applied |
| 📤 Applied | Application sent |
| 💬 Interview | Interview scheduled or done |
| 🎉 Offer | Received an offer |
| ❌ Rejected | Not moving forward |
| 👻 No Response | Applied, heard nothing |

---

## Troubleshooting

**"Adzuna API key error"** → Check your App ID and App Key in `config.py`

**"Google Maps not configured"** → That's okay! The agent still works without it. Add the key to enable startup discovery.

**"Could not extract jobs from career page"** → Some pages use JavaScript to load jobs. The scraper works best on simple HTML career pages.

**Jobs not found** → Try increasing `max_days_old` to 3 or 7 for more results.
