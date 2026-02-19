# ─── Dockerfile ───────────────────────────────────────────────────────────────
# Deploys the AI Job Search Agent to Azure Container Instances
# Runs 24/7, checks for new jobs on your schedule, emails you alerts

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all agent files
COPY . .

# Create directories for generated files
RUN mkdir -p cover_letters tailored_resumes interview_prep

# Environment variables (set these in Azure Portal or .env)
# These are placeholders — set real values in Azure
ENV ANTHROPIC_API_KEY=""
ENV NOTIFY_EMAIL_FROM=""
ENV NOTIFY_EMAIL_PASSWORD=""
ENV NOTIFY_EMAIL_TO=""
ENV NOTIFY_EMAIL_PROVIDER="gmail"
ENV ADZUNA_APP_ID=""
ENV ADZUNA_APP_KEY=""
ENV GOOGLE_MAPS_API_KEY=""

# Run the cloud monitor (not the interactive menu)
CMD ["python", "cloud_runner.py"]
