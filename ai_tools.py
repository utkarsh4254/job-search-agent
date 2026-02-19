"""
ai_tools.py — Claude-Powered Career Tools
==========================================
• Job Match Scorer      — Score resume vs job description (0-100%)
• Resume Tailor         — Rewrite resume bullets to match job keywords
• Cover Letter Writer   — Generate personalized cover letters
• Interview Prep        — Generate likely interview questions + answers
"""

import anthropic
import json
import os
from datetime import datetime

client = anthropic.Anthropic()
RESUME_FILE       = "my_resume.txt"
COVER_LETTERS_DIR = "cover_letters"
INTERVIEW_DIR     = "interview_prep"

# ─── Colors ────────────────────────────────────────────────────────────────────
class C:
    BOLD   = "\033[1m"; BLUE  = "\033[94m"; CYAN  = "\033[96m"
    GREEN  = "\033[92m"; YELLOW= "\033[93m"; RED   = "\033[91m"
    GRAY   = "\033[90m"; RESET = "\033[0m"

def bold(t):   return f"{C.BOLD}{t}{C.RESET}"
def cyan(t):   return f"{C.CYAN}{t}{C.RESET}"
def green(t):  return f"{C.GREEN}{t}{C.RESET}"
def yellow(t): return f"{C.YELLOW}{t}{C.RESET}"
def gray(t):   return f"{C.GRAY}{t}{C.RESET}"
def red(t):    return f"{C.RED}{t}{C.RESET}"

def pause(): input(f"\n  {gray('Press Enter to continue...')}")
def clear(): os.system("cls" if os.name == "nt" else "clear")

def header(title):
    print(f"\n{bold(C.BLUE + '═' * 62 + C.RESET)}")
    print(f"  {bold(cyan('🤖 CAREER ASSISTANT'))}  {gray(title)}")
    print(f"{bold(C.BLUE + '═' * 62 + C.RESET)}\n")


# ─── Resume Loader ─────────────────────────────────────────────────────────────
def load_resume() -> str:
    """Load resume from file, or prompt user to paste it."""
    if os.path.exists(RESUME_FILE):
        with open(RESUME_FILE, "r") as f:
            return f.read().strip()
    return ""

def ensure_resume() -> str:
    """Make sure we have a resume, prompt if not."""
    resume = load_resume()
    if resume:
        return resume

    clear()
    header("Resume Setup")
    print(f"  {yellow('⚠  No resume found.')}")
    print(f"  {gray('Paste your resume below, then press Enter twice when done.')}\n")
    print(f"  {gray('(This will be saved to my_resume.txt for future use)')}\n")

    lines = []
    while True:
        line = input("  ")
        if not line and lines:
            break
        lines.append(line)

    resume = "\n".join(lines)
    with open(RESUME_FILE, "w") as f:
        f.write(resume)
    print(green("\n  ✅ Resume saved!"))
    return resume

def get_job_description(job: dict) -> str:
    """Get job description — from saved notes or ask user to paste."""
    if job.get("description"):
        return job["description"]

    print(f"\n  {gray('Paste the job description below, then press Enter twice:')}\n")
    lines = []
    while True:
        line = input("  ")
        if not line and lines:
            break
        lines.append(line)
    return "\n".join(lines)


# ─── 1. JOB MATCH SCORER ──────────────────────────────────────────────────────
def score_job_match(job: dict) -> dict:
    """
    Use Claude to score how well the user's resume matches a job.
    Returns score, matched keywords, missing skills, recommendation.
    """
    clear()
    header(f"Job Match Scorer — {job['title']} @ {job['company']}")

    resume = ensure_resume()
    print(f"\n  {cyan('Paste the job description for this role:')}")
    jd = get_job_description(job)

    print(f"\n  {gray('🤖 Analysing match...')}\n")

    prompt = f"""You are an expert ATS (Applicant Tracking System) and career coach.

Analyse how well this resume matches the job description and return a JSON object ONLY (no other text).

RESUME:
{resume}

JOB DESCRIPTION:
{jd}

Return this exact JSON structure:
{{
  "score": <integer 0-100>,
  "grade": "<A/B/C/D/F>",
  "verdict": "<one sentence summary>",
  "matched_keywords": ["keyword1", "keyword2", ...],
  "missing_skills": ["skill1", "skill2", ...],
  "strengths": ["strength1", "strength2", "strength3"],
  "weaknesses": ["weakness1", "weakness2", "weakness3"],
  "recommendation": "<2-3 sentence actionable advice>"
}}"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {"score": 0, "grade": "?", "verdict": raw, "matched_keywords": [],
                  "missing_skills": [], "strengths": [], "weaknesses": [], "recommendation": raw}

    # Display results
    score = result.get("score", 0)
    grade = result.get("grade", "?")

    if score >= 80:
        score_color = C.GREEN
        bar_char = "█"
    elif score >= 60:
        score_color = C.YELLOW
        bar_char = "█"
    else:
        score_color = C.RED
        bar_char = "█"

    bar = f"{score_color}{bar_char * (score // 5)}{C.GRAY}{'░' * (20 - score // 5)}{C.RESET}"

    print(f"  {bold('Match Score:')}  {score_color}{bold(f'{score}/100  Grade: {grade}')}{C.RESET}")
    print(f"  {bar}\n")
    print(f"  {bold('Verdict:')}  {result.get('verdict', '')}\n")

    if result.get("matched_keywords"):
        print(f"  {bold(green('✅ Matched Keywords:'))}")
        print(f"  {gray(', '.join(result['matched_keywords']))}\n")

    if result.get("missing_skills"):
        print(f"  {bold(red('❌ Missing Skills:'))}")
        print(f"  {gray(', '.join(result['missing_skills']))}\n")

    if result.get("strengths"):
        print(f"  {bold('💪 Strengths:')}")
        for s in result["strengths"]:
            print(f"    {green('•')} {s}")
        print()

    if result.get("weaknesses"):
        print(f"  {bold('⚠  Gaps:')}")
        for w in result["weaknesses"]:
            print(f"    {yellow('•')} {w}")
        print()

    if result.get("recommendation"):
        print(f"  {bold('💡 Recommendation:')}")
        print(f"  {result['recommendation']}\n")

    # Save score to job
    result["scored_at"] = datetime.now().isoformat()
    result["job_description"] = jd

    pause()
    return result


# ─── 2. RESUME TAILOR ─────────────────────────────────────────────────────────
def tailor_resume(job: dict) -> str:
    """
    Use Claude to rewrite resume bullet points to better match this job.
    Returns the tailored resume as a string.
    """
    clear()
    header(f"Resume Tailor — {job['title']} @ {job['company']}")

    resume = ensure_resume()
    print(f"\n  {cyan('Paste the job description:')}")
    jd = get_job_description(job)

    print(f"\n  {gray('🤖 Tailoring your resume...')}\n")

    prompt = f"""You are an expert resume writer and career coach.

Rewrite the resume below to better match the job description. Follow these rules:
1. Keep all the same jobs, companies, dates and education — do NOT invent anything
2. Rewrite bullet points to use keywords from the job description naturally
3. Reorder bullets so the most relevant ones come first
4. Add ATS-friendly keywords from the job description where they genuinely apply
5. Keep the same format and structure
6. Make it sound natural and human, not keyword-stuffed

ORIGINAL RESUME:
{resume}

JOB DESCRIPTION:
{jd}

Output the full tailored resume only. No explanations, no preamble."""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    tailored = response.content[0].text.strip()

    # Save to file
    os.makedirs("tailored_resumes", exist_ok=True)
    safe_company = "".join(c for c in job["company"] if c.isalnum() or c in " _-").strip()
    filename = f"tailored_resumes/resume_{safe_company}_{datetime.now().strftime('%Y%m%d')}.txt"

    with open(filename, "w") as f:
        f.write(f"TAILORED RESUME FOR: {job['title']} at {job['company']}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(tailored)

    print(f"  {bold('📄 Tailored Resume Preview:')}\n")
    print(f"  {gray('─' * 55)}")
    # Show first 40 lines
    lines = tailored.split("\n")
    for line in lines[:40]:
        print(f"  {line}")
    if len(lines) > 40:
        print(f"  {gray(f'... ({len(lines) - 40} more lines)')}")
    print(f"  {gray('─' * 55)}")

    print(f"\n  {green(f'✅ Saved to: {filename}')}")
    pause()
    return tailored


# ─── 3. COVER LETTER GENERATOR ────────────────────────────────────────────────
def generate_cover_letter(job: dict) -> str:
    """
    Generate a personalized cover letter for a specific job.
    """
    clear()
    header(f"Cover Letter — {job['title']} @ {job['company']}")

    resume = ensure_resume()
    print(f"\n  {cyan('Paste the job description:')}")
    jd = get_job_description(job)

    # Get user name from resume or ask
    print(f"\n  {gray('A few quick questions for personalization:')}\n")
    user_name    = input(f"  {bold('→')} Your full name: ").strip()
    hiring_mgr   = input(f"  {bold('→')} Hiring manager name (or press Enter for 'Hiring Team'): ").strip() or "Hiring Team"
    tone_choice  = input(f"  {bold('→')} Tone — [1] Professional  [2] Enthusiastic  [3] Concise: ").strip()
    tone_map     = {"1": "professional and formal", "2": "enthusiastic and energetic", "3": "concise and direct"}
    tone         = tone_map.get(tone_choice, "professional and formal")

    print(f"\n  {gray('🤖 Writing your cover letter...')}\n")

    prompt = f"""Write a compelling, personalized cover letter for this job application.

Applicant Name: {user_name}
Hiring Manager: {hiring_mgr}
Tone: {tone}

APPLICANT'S RESUME:
{resume}

JOB DESCRIPTION:
{jd}

Instructions:
- Open with a strong hook that shows genuine interest in THIS company specifically
- Connect 2-3 specific experiences from the resume to the job requirements
- Show knowledge of what the company does and why you want to work there
- Close with a confident call to action
- Keep it to 3-4 short paragraphs (under 350 words)
- Do NOT use clichés like "I am writing to express my interest"
- Sound like a real human, not a template
- Address it to: {hiring_mgr}

Write the cover letter only. No explanations."""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    letter = response.content[0].text.strip()

    # Save to file
    os.makedirs(COVER_LETTERS_DIR, exist_ok=True)
    safe_company = "".join(c for c in job["company"] if c.isalnum() or c in " _-").strip()
    filename = f"{COVER_LETTERS_DIR}/cover_{safe_company}_{datetime.now().strftime('%Y%m%d')}.txt"

    with open(filename, "w") as f:
        f.write(letter)

    # Display
    print(f"  {bold('✉️  Your Cover Letter:')}\n")
    print(f"  {gray('─' * 55)}")
    for line in letter.split("\n"):
        print(f"  {line}")
    print(f"  {gray('─' * 55)}")
    print(f"\n  {green(f'✅ Saved to: {filename}')}")
    pause()
    return letter


# ─── 4. INTERVIEW PREP ────────────────────────────────────────────────────────
def generate_interview_prep(job: dict) -> str:
    """
    Generate likely interview questions + suggested answers for a job.
    """
    clear()
    header(f"Interview Prep — {job['title']} @ {job['company']}")

    resume = ensure_resume()
    print(f"\n  {cyan('Paste the job description:')}")
    jd = get_job_description(job)

    print(f"\n  {gray('🤖 Generating interview questions and answers...')}\n")

    prompt = f"""You are an expert interview coach preparing a candidate for a job interview.

Generate a comprehensive interview preparation guide for this role.

CANDIDATE'S RESUME:
{resume}

JOB DESCRIPTION:
{jd}
COMPANY: {job['company']}
ROLE: {job['title']}

Create the following sections:

## 1. LIKELY INTERVIEW QUESTIONS (10 questions)
For each question:
- The question
- Why they ask it
- A suggested answer framework using the STAR method (Situation, Task, Action, Result)
- Key points to mention from the resume

Include a mix of:
- Behavioural questions ("Tell me about a time...")
- Technical questions specific to this role
- Company/culture fit questions
- "Why this company?" type questions

## 2. QUESTIONS TO ASK THE INTERVIEWER (5 smart questions)
Questions that show genuine interest and intelligence.

## 3. KEY THINGS TO RESEARCH BEFORE THE INTERVIEW
What to look up about the company, team, and role.

## 4. RED FLAGS TO WATCH FOR
Things in this role/company description that might be worth clarifying.

Be specific to THIS role and company. Not generic advice."""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    prep = response.content[0].text.strip()

    # Save to file
    os.makedirs(INTERVIEW_DIR, exist_ok=True)
    safe_company = "".join(c for c in job["company"] if c.isalnum() or c in " _-").strip()
    filename = f"{INTERVIEW_DIR}/prep_{safe_company}_{datetime.now().strftime('%Y%m%d')}.txt"

    with open(filename, "w") as f:
        f.write(f"INTERVIEW PREP: {job['title']} at {job['company']}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(prep)

    # Show preview
    print(f"  {bold('🎤 Interview Prep Guide Preview:')}\n")
    print(f"  {gray('─' * 55)}")
    lines = prep.split("\n")
    for line in lines[:50]:
        display = line
        if line.startswith("##"):
            display = bold(cyan(line))
        elif line.startswith("**") or line.startswith("###"):
            display = bold(line.replace("**", "").replace("###", "").strip())
        print(f"  {display}")
    if len(lines) > 50:
        print(f"\n  {gray(f'... ({len(lines) - 50} more lines in the saved file)')}")
    print(f"  {gray('─' * 55)}")
    print(f"\n  {green(f'✅ Full guide saved to: {filename}')}")
    pause()
    return prep


# ─── AI Tools Menu ─────────────────────────────────────────────────────────────
def ai_tools_menu(job: dict, jobs: list) -> list:
    """Sub-menu for all AI career tools for a specific job."""
    while True:
        clear()
        header(f"AI Tools — {job['title']} @ {job['company']}")

        score = job.get("match_score")
        score_str = f"{green(str(score) + '%')}" if score else gray("Not scored")

        print(f"  {bold('Job:')}    {cyan(job['title'])} at {bold(job['company'])}")
        print(f"  {bold('Match:')}  {score_str}\n")

        print(f"  {bold('[1]')} 🎯 Score my resume match")
        print(f"  {bold('[2]')} 📄 Tailor my resume for this job")
        print(f"  {bold('[3]')} ✉️  Generate cover letter")
        print(f"  {bold('[4]')} 🎤 Generate interview prep")
        print(f"  {bold('[5]')} 📋 Do ALL of the above")
        print(f"  {bold('[0]')} Back\n")

        choice = input(f"  {bold('→')} Choose: ").strip()

        if choice == "1":
            result = score_job_match(job)
            job["match_score"]      = result.get("score")
            job["match_grade"]      = result.get("grade")
            job["matched_keywords"] = result.get("matched_keywords", [])
            job["missing_skills"]   = result.get("missing_skills", [])

        elif choice == "2":
            tailor_resume(job)

        elif choice == "3":
            letter = generate_cover_letter(job)
            job["cover_letter_generated"] = True

        elif choice == "4":
            generate_interview_prep(job)
            job["interview_prep_generated"] = True

        elif choice == "5":
            print(f"\n  {cyan('Running all AI tools...')}\n")
            result = score_job_match(job)
            job["match_score"]      = result.get("score")
            job["match_grade"]      = result.get("grade")
            job["matched_keywords"] = result.get("matched_keywords", [])
            job["missing_skills"]   = result.get("missing_skills", [])
            tailor_resume(job)
            generate_cover_letter(job)
            generate_interview_prep(job)
            job["cover_letter_generated"]  = True
            job["interview_prep_generated"] = True
            print(green("\n  ✅ All AI tools complete! Check your folders for saved files."))
            pause()

        elif choice == "0":
            break

        # Save updated job back to list
        for i, j in enumerate(jobs):
            if j["id"] == job["id"]:
                jobs[i] = job
                break

        # Persist — local import to avoid circular dependency
        import json
        with open('saved_jobs.json', 'w') as _f:
            for idx, _j in enumerate(jobs): _j['id'] = idx + 1
            json.dump(jobs, _f, indent=2)

    return jobs
