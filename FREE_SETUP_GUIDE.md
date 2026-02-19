# 🆓 Free Setup Guide — AI Job Search Agent

Everything runs **100% free**. No credit card. No paid subscriptions.

---

## Free Stack Overview

| What | Free Service | Limit |
|------|-------------|-------|
| AI Brain (primary) | **Groq** — Llama 3.3 70B | 30 req/min, forever free |
| AI Brain (fallback) | **Gemini** — 1.5 Flash | 15 req/min, 1M tokens/day |
| Job Board Search | **Adzuna** free tier | 250 calls/month |
| Remote Jobs | **RemoteOK** public API | Unlimited |
| Startup Jobs | **Hacker News** Algolia API | Unlimited |
| YC Startups | **Wellfound** scraping | Unlimited |
| Job aggregator | **Indeed** RSS feed | Unlimited |
| 24/7 Hosting | **GitHub Actions** | 2,000 min/month free |
| Data Storage | **GitHub repo** (JSON file) | Unlimited |
| Notifications | **Gmail** SMTP | Free forever |

**Total monthly cost: $0.00** 🎉

---

## Step-by-Step Setup (20 minutes total)

### Step 1 — Get Groq API key (5 min) 🟡

1. Go to **https://console.groq.com**
2. Click **Sign Up** — no credit card needed
3. Go to **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_...`)

### Step 2 — Get Gemini API key (3 min) 🔵

1. Go to **https://aistudio.google.com/app/apikey**
2. Sign in with Google
3. Click **Create API Key**
4. Copy the key (starts with `AIza...`)

### Step 3 — Get Adzuna key (5 min) 📋

1. Go to **https://developer.adzuna.com/signup**
2. Fill in the form (it's free)
3. You'll get an **App ID** and **App Key** by email
4. Copy both

### Step 4 — Set up Gmail App Password (3 min) 📧

> Regular password won't work — Gmail requires an App Password for SMTP

1. Go to your **Google Account → Security**
2. Make sure **2-Step Verification** is ON
3. Search for **App Passwords**
4. Select app: **Mail** | Device: **Other** → name it "Job Agent"
5. Copy the 16-character password

### Step 5 — Push to GitHub (2 min)

```bash
# Create a new repo on github.com, then:
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/job-search-agent.git
git push -u origin main
```

### Step 6 — Add secrets to GitHub (3 min) 🔑

Go to your repo on GitHub:
**Settings → Secrets and variables → Actions → New repository secret**

Add these one by one:

| Secret Name | Value |
|-------------|-------|
| `GROQ_API_KEY` | Your Groq key (`gsk_...`) |
| `GEMINI_API_KEY` | Your Gemini key (`AIza...`) |
| `ADZUNA_APP_ID` | Your Adzuna App ID |
| `ADZUNA_APP_KEY` | Your Adzuna App Key |
| `NOTIFY_EMAIL_FROM` | Your Gmail address |
| `NOTIFY_EMAIL_PASSWORD` | Your Gmail App Password (16 chars) |
| `NOTIFY_EMAIL_TO` | Where to send alerts (can be same email) |
| `NOTIFY_EMAIL_PROVIDER` | `gmail` |

### Step 7 — Customize search settings

Open `.github/workflows/job_search.yml` and edit these lines:

```yaml
SEARCH_KEYWORDS: "Python developer"    # ← Your job title
SEARCH_LOCATION: "London"              # ← Your city (blank = anywhere)
SEARCH_INDUSTRY: "fintech startup"     # ← For startup discovery
MAX_JOB_AGE_DAYS: "1"                 # ← Only jobs from last 24 hours
```

### Step 8 — Enable GitHub Actions

1. Go to your repo → **Actions** tab
2. Click **Enable Actions**
3. The workflow will run automatically every 30 minutes!

---

## Verifying It Works

**Run it manually first:**
1. Go to **Actions → Job Search Agent → Run workflow**
2. Click **Run workflow**
3. Watch the logs — you should see jobs being found!
4. Check your email for a notification

**Check your saved jobs:**
- After the first run, `saved_jobs.json` will appear in your repo
- You can view it directly on GitHub or run `python job_manager.py` locally

---

## GitHub Actions Free Limits

- **2,000 minutes/month** free for public repos
- **500 minutes/month** for private repos
- Running every 30 min = ~1,440 minutes/month for public repos ✅
- You have ~560 minutes buffer for manual runs

> 💡 **Tip:** Make your repo **public** to get 2,000 free minutes (job data is not sensitive — it's just job listings)

---

## Running Locally (optional)

```bash
# Set your keys
export GROQ_API_KEY="gsk_..."
export GEMINI_API_KEY="AIza..."
export ADZUNA_APP_ID="your-id"
export ADZUNA_APP_KEY="your-key"

# Install
pip install -r requirements.txt

# Run
python launch.py          # Full interactive menu
python job_manager.py     # Manage saved jobs
python reminders.py       # Check follow-up reminders
```

---

## Troubleshooting

**"No module named groq"**
```bash
pip install groq google-generativeai
```

**"GROQ_API_KEY not set"**
→ Add it to GitHub Secrets (Step 6)

**"Adzuna API key error"**
→ Get free keys at developer.adzuna.com/signup

**No email received**
→ Check `NOTIFY_EMAIL_PASSWORD` is the App Password, not your login password

**GitHub Actions not running**
→ Go to Actions tab → make sure it's enabled → check the workflow file is in `.github/workflows/`

**Rate limit on Groq**
→ The system automatically falls back to Gemini — no action needed
