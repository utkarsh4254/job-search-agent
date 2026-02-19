"""
notifications.py — Email Notification System
=============================================
Sends email alerts via Gmail or Outlook when:
  • A new job is found matching your filters
  • A follow-up reminder is due (7 days no response)
  • An interview is scheduled
  • Weekly digest of your job search progress

Supports: Gmail, Outlook/Hotmail, any SMTP server
"""

import smtplib
import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import List

# ─── Load from environment variables (set these in Azure) ──────────────────────
EMAIL_FROM     = os.environ.get("NOTIFY_EMAIL_FROM", "")      # your Gmail/Outlook
EMAIL_PASSWORD = os.environ.get("NOTIFY_EMAIL_PASSWORD", "")  # app password
EMAIL_TO       = os.environ.get("NOTIFY_EMAIL_TO", "")        # where to send alerts
EMAIL_PROVIDER = os.environ.get("NOTIFY_EMAIL_PROVIDER", "gmail")  # gmail | outlook


# ─── SMTP Config ───────────────────────────────────────────────────────────────
SMTP_CONFIG = {
    "gmail": {
        "host": "smtp.gmail.com",
        "port": 587,
        "tls":  True,
    },
    "outlook": {
        "host": "smtp-mail.outlook.com",
        "port": 587,
        "tls":  True,
    },
    "hotmail": {
        "host": "smtp-mail.outlook.com",
        "port": 587,
        "tls":  True,
    },
    "yahoo": {
        "host": "smtp.mail.yahoo.com",
        "port": 587,
        "tls":  True,
    },
}


# ─── Core Send Function ────────────────────────────────────────────────────────
def send_email(subject: str, html_body: str, text_body: str = "") -> bool:
    """
    Send an email notification.
    Returns True if sent successfully, False otherwise.
    """
    if not EMAIL_FROM or not EMAIL_PASSWORD or not EMAIL_TO:
        print("⚠️  Email not configured. Set NOTIFY_EMAIL_FROM, NOTIFY_EMAIL_PASSWORD, NOTIFY_EMAIL_TO")
        return False

    config = SMTP_CONFIG.get(EMAIL_PROVIDER.lower(), SMTP_CONFIG["gmail"])

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"Job Search Agent <{EMAIL_FROM}>"
        msg["To"]      = EMAIL_TO

        # Plain text fallback
        if text_body:
            msg.attach(MIMEText(text_body, "plain"))

        # HTML version
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(config["host"], config["port"]) as server:
            if config["tls"]:
                server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

        print(f"✅ Email sent: {subject}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("❌ Email auth failed. Check your email/password.")
        print("   Gmail users: Use an App Password, not your regular password.")
        print("   Guide: https://support.google.com/accounts/answer/185833")
        return False
    except Exception as e:
        print(f"❌ Email send error: {e}")
        return False


# ─── Email Templates ───────────────────────────────────────────────────────────
def _base_template(title: str, content: str) -> str:
    """Wrap content in a clean HTML email template."""
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
          background: #f5f5f5; margin: 0; padding: 20px; color: #333; }}
  .container {{ max-width: 600px; margin: 0 auto; background: white;
                border-radius: 12px; overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
  .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
             color: white; padding: 28px 32px; }}
  .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; }}
  .header p  {{ margin: 6px 0 0; opacity: 0.75; font-size: 13px; }}
  .body   {{ padding: 28px 32px; }}
  .job-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-left: 4px solid #3b82f6;
               border-radius: 8px; padding: 16px 20px; margin: 14px 0; }}
  .job-title {{ font-size: 16px; font-weight: 700; color: #1e293b; margin: 0 0 4px; }}
  .job-company {{ font-size: 14px; color: #3b82f6; font-weight: 600; margin: 0 0 8px; }}
  .job-meta {{ font-size: 13px; color: #64748b; line-height: 1.6; }}
  .job-meta span {{ margin-right: 14px; }}
  .btn {{ display: inline-block; background: #3b82f6; color: white !important;
          text-decoration: none; padding: 10px 20px; border-radius: 6px;
          font-size: 13px; font-weight: 600; margin-top: 10px; }}
  .btn:hover {{ background: #2563eb; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px;
            font-size: 11px; font-weight: 700; text-transform: uppercase; }}
  .badge-new     {{ background: #dcfce7; color: #166534; }}
  .badge-urgent  {{ background: #fef3c7; color: #92400e; }}
  .badge-startup {{ background: #ede9fe; color: #5b21b6; }}
  .stat-row {{ display: flex; gap: 12px; margin: 16px 0; }}
  .stat-box {{ flex: 1; background: #f1f5f9; border-radius: 8px; padding: 14px;
               text-align: center; }}
  .stat-num {{ font-size: 24px; font-weight: 800; color: #1e293b; }}
  .stat-lbl {{ font-size: 11px; color: #64748b; text-transform: uppercase;
               font-weight: 600; margin-top: 2px; }}
  .footer {{ background: #f8fafc; border-top: 1px solid #e2e8f0;
             padding: 16px 32px; font-size: 12px; color: #94a3b8; text-align: center; }}
  h2 {{ color: #1e293b; font-size: 17px; margin: 24px 0 12px; }}
  .divider {{ border: none; border-top: 1px solid #e2e8f0; margin: 20px 0; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🤖 {title}</h1>
    <p>AI Job Search Agent • {datetime.now().strftime("%A, %B %d %Y • %I:%M %p")}</p>
  </div>
  <div class="body">
    {content}
  </div>
  <div class="footer">
    Sent by your AI Job Search Agent running on Azure •
    <a href="#" style="color:#94a3b8;">Manage notifications</a>
  </div>
</div>
</body>
</html>
"""


# ─── 1. New Jobs Alert ─────────────────────────────────────────────────────────
def notify_new_jobs(jobs: list, search_query: str = "") -> bool:
    """Send an email alert when new jobs are found."""
    if not jobs:
        return False

    count = len(jobs)
    subject = f"🎯 {count} New Job{'s' if count > 1 else ''} Found — {search_query}"

    # Build job cards HTML
    cards_html = ""
    cards_text = ""

    for job in jobs[:10]:  # Max 10 jobs per email
        title    = job.get("title", "Unknown Role")
        company  = job.get("company", "Unknown Company")
        location = job.get("location", "Remote")
        source   = job.get("source", "Job Board")
        url      = job.get("url", "#")
        notes    = job.get("notes", "")

        # Badge based on source
        if "Maps" in source or "Startup" in source:
            badge = '<span class="badge badge-startup">🗺 Startup</span>'
        elif "Hacker" in source or "YC" in source or "Wellfound" in source:
            badge = '<span class="badge badge-startup">🟠 YC/HN</span>'
        else:
            badge = '<span class="badge badge-new">⚡ New</span>'

        link_btn = f'<a href="{url}" class="btn">View Job →</a>' if url and url != "#" else ""

        cards_html += f"""
        <div class="job-card">
          <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <p class="job-title">{title}</p>
            {badge}
          </div>
          <p class="job-company">{company}</p>
          <div class="job-meta">
            <span>📍 {location}</span>
            <span>📡 {source}</span>
          </div>
          {f'<p style="margin:8px 0 0; font-size:13px; color:#475569;">{notes}</p>' if notes else ''}
          {link_btn}
        </div>"""

        cards_text += f"• {title} at {company} ({location})\n  {url}\n\n"

    content = f"""
    <p style="font-size:15px; color:#374151;">
      Your job search agent found <strong>{count} new job{'s' if count > 1 else ''}</strong>
      {f'matching <strong>{search_query}</strong>' if search_query else ''}.
    </p>
    <h2>New Opportunities</h2>
    {cards_html}
    <hr class="divider">
    <p style="font-size:13px; color:#64748b; margin:0;">
      💡 <strong>Tip:</strong> Apply within 24 hours — early applicants get 3× more responses.
    </p>
    """

    text = f"New Jobs Found!\n\n{cards_text}\nSearch: {search_query}"
    return send_email(subject, _base_template(f"{count} New Job{'s' if count > 1 else ''} Found", content), text)


# ─── 2. Follow-Up Reminder Email ──────────────────────────────────────────────
def notify_followup_due(jobs: list) -> bool:
    """Send email when jobs need a follow-up."""
    if not jobs:
        return False

    count = len(jobs)
    subject = f"🔔 {count} Job{'s' if count > 1 else ''} Need a Follow-Up Email"

    rows_html = ""
    for job in jobs:
        days = job.get("_days_since", 7)
        urgency_color = "#ef4444" if days > 14 else "#f59e0b"
        rows_html += f"""
        <div class="job-card" style="border-left-color: {urgency_color};">
          <p class="job-title">{job.get('title', 'N/A')}</p>
          <p class="job-company">{job.get('company', 'N/A')}</p>
          <div class="job-meta">
            <span>⏰ Applied <strong>{days} days ago</strong></span>
            <span>📍 {job.get('location', 'Remote')}</span>
          </div>
          {f'<a href="{job["url"]}" class="btn" style="background:{urgency_color};">View Job →</a>' if job.get("url") else ''}
        </div>"""

    content = f"""
    <p style="font-size:15px; color:#374151;">
      You applied to <strong>{count} job{'s' if count > 1 else ''}</strong> over 7 days ago
      and haven't heard back. A short follow-up email can <strong>3× your response rate</strong>.
    </p>
    <h2>Follow Up On These</h2>
    {rows_html}
    <hr class="divider">
    <div style="background:#fef3c7; border-radius:8px; padding:16px; margin-top:16px;">
      <p style="margin:0; font-size:13px; color:#92400e;">
        <strong>📝 Quick follow-up template:</strong><br><br>
        Hi [Name], I wanted to follow up on my application for the [Role] position.
        I'm still very interested and would love to learn about next steps.
        Happy to provide any additional information. Thank you!
      </p>
    </div>
    """

    text = f"Follow-up needed for {count} jobs:\n\n" + \
           "\n".join([f"• {j.get('title')} at {j.get('company')} ({j.get('_days_since', 7)} days ago)" for j in jobs])

    return send_email(subject, _base_template("Follow-Up Reminders", content), text)


# ─── 3. Weekly Digest ─────────────────────────────────────────────────────────
def notify_weekly_digest(jobs: list) -> bool:
    """Send a weekly summary of job search progress."""
    if not jobs:
        return False

    counts = {}
    for job in jobs:
        s = job.get("status", "Saved")
        counts[s] = counts.get(s, 0) + 1

    total       = len(jobs)
    applied     = counts.get("Applied", 0)
    interviews  = counts.get("Interview", 0)
    offers      = counts.get("Offer", 0)
    rejected    = counts.get("Rejected", 0)
    no_response = counts.get("No Response", 0)

    # Response rate
    response_rate = round(((interviews + offers) / applied * 100)) if applied > 0 else 0

    subject = f"📊 Weekly Job Search Digest — {applied} Applied, {interviews} Interviews"

    # Recent activity (last 7 days)
    recent = [j for j in jobs if j.get("saved_at", "")[:10] >= 
              (datetime.now().strftime("%Y-%m-%d")[:8] + "01")][:5]

    recent_html = "".join([
        f'<div style="padding:8px 0; border-bottom:1px solid #f1f5f9; font-size:13px;">'
        f'<strong>{j.get("title")}</strong> at {j.get("company")} '
        f'<span style="color:#3b82f6;">({j.get("status")})</span></div>'
        for j in recent
    ]) or "<p style='color:#94a3b8; font-size:13px;'>No recent activity</p>"

    content = f"""
    <p style="font-size:15px; color:#374151;">
      Here's your job search summary for the week. Keep going — consistency wins! 💪
    </p>

    <div class="stat-row">
      <div class="stat-box">
        <div class="stat-num" style="color:#3b82f6;">{total}</div>
        <div class="stat-lbl">Total Saved</div>
      </div>
      <div class="stat-box">
        <div class="stat-num" style="color:#8b5cf6;">{applied}</div>
        <div class="stat-lbl">Applied</div>
      </div>
      <div class="stat-box">
        <div class="stat-num" style="color:#f59e0b;">{interviews}</div>
        <div class="stat-lbl">Interviews</div>
      </div>
      <div class="stat-box">
        <div class="stat-num" style="color:#10b981;">{offers}</div>
        <div class="stat-lbl">Offers</div>
      </div>
    </div>

    <div style="background:#f0f9ff; border-radius:8px; padding:16px; margin:16px 0;">
      <p style="margin:0; font-size:14px; color:#0369a1;">
        <strong>📈 Response Rate: {response_rate}%</strong>
        {'  🔥 Excellent!' if response_rate > 20 else '  Keep applying!' if response_rate > 10 else '  Try tailoring your resume more.'}
      </p>
    </div>

    <h2>Recent Activity</h2>
    {recent_html}

    <hr class="divider">
    <h2>This Week's Goal</h2>
    <p style="font-size:13px; color:#374151; line-height:1.7;">
      {'🎯 You have interviews! Focus on prep.' if interviews > 0 else
       '📤 Apply to 5 more jobs and follow up on existing ones.' if applied > 0 else
       '🚀 Start applying! Aim for 5 applications this week.'}
    </p>
    """

    text = f"Weekly Digest: {total} saved, {applied} applied, {interviews} interviews, {offers} offers"
    return send_email(subject, _base_template("Weekly Job Search Digest", content), text)


# ─── 4. Test Notification ─────────────────────────────────────────────────────
def send_test_email() -> bool:
    """Send a test email to verify everything is configured correctly."""
    content = """
    <p style="font-size:15px; color:#374151;">
      ✅ Your AI Job Search Agent notifications are working perfectly!
    </p>
    <div class="job-card">
      <p class="job-title">Senior Software Engineer (Example)</p>
      <p class="job-company">Stripe</p>
      <div class="job-meta">
        <span>📍 Remote</span>
        <span>⚡ Posted 2 hours ago</span>
        <span>📡 Job Board</span>
      </div>
    </div>
    <p style="font-size:13px; color:#64748b;">
      This is what a real job alert will look like. Your agent is now running 24/7 on Azure
      and will email you the moment new jobs are found.
    </p>
    """
    return send_email(
        "✅ Job Agent Notifications Working!",
        _base_template("Test Notification", content),
        "Your job search agent is configured and working!"
    )


# ─── Config Checker ───────────────────────────────────────────────────────────
def check_config() -> dict:
    """Return status of notification configuration."""
    return {
        "from":     EMAIL_FROM or None,
        "to":       EMAIL_TO or None,
        "provider": EMAIL_PROVIDER,
        "ready":    bool(EMAIL_FROM and EMAIL_PASSWORD and EMAIL_TO)
    }


if __name__ == "__main__":
    print("Testing email notification...")
    cfg = check_config()
    if not cfg["ready"]:
        print("\n❌ Email not fully configured. Set these environment variables:")
        print("   NOTIFY_EMAIL_FROM      — your Gmail or Outlook address")
        print("   NOTIFY_EMAIL_PASSWORD  — your app password (not login password)")
        print("   NOTIFY_EMAIL_TO        — where to send alerts")
        print("   NOTIFY_EMAIL_PROVIDER  — gmail | outlook | yahoo (default: gmail)")
        print("\n📖 Gmail App Password guide:")
        print("   https://support.google.com/accounts/answer/185833")
    else:
        print(f"From: {cfg['from']}")
        print(f"To:   {cfg['to']}")
        result = send_test_email()
        if result:
            print("✅ Test email sent! Check your inbox.")
        else:
            print("❌ Failed. Check credentials above.")
