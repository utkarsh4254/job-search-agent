#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  deploy_azure.sh — Deploy Job Search Agent to Azure
#  Run this once and your agent runs 24/7 on Azure
#
#  Prerequisites:
#    • Azure CLI installed: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli
#    • Docker installed: https://www.docker.com/get-started
#    • Azure account (free tier works!)
#
#  Usage:
#    chmod +x deploy_azure.sh
#    ./deploy_azure.sh
# ═══════════════════════════════════════════════════════════════

set -e  # Exit on any error

# ─── CONFIGURATION — Edit these before running ─────────────────────────────────
RESOURCE_GROUP="job-search-agent-rg"
CONTAINER_NAME="job-search-agent"
REGISTRY_NAME="jobsearchagentregistry"   # Must be globally unique — change this!
LOCATION="eastus"                         # Azure region
IMAGE_NAME="job-search-agent"

# ─── COLORS ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

echo -e "\n${BOLD}${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║     🤖 AI JOB AGENT — AZURE DEPLOYMENT WIZARD        ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════╝${NC}\n"

# ─── Collect secrets interactively ────────────────────────────────────────────
echo -e "${BOLD}Step 1: Enter your API keys and settings${NC}"
echo -e "${YELLOW}(These will be stored securely in Azure — not in any file)${NC}\n"

read -p "🔑 Anthropic API key (sk-ant-...): " ANTHROPIC_KEY
read -p "📧 Your Gmail/Outlook address:     " EMAIL_FROM
read -s -p "🔒 Email App Password:             " EMAIL_PASS; echo
read -p "📬 Send alerts to (email):         " EMAIL_TO
read -p "📡 Email provider (gmail/outlook): " EMAIL_PROVIDER
EMAIL_PROVIDER=${EMAIL_PROVIDER:-gmail}

echo ""
read -p "🔍 Job keywords (e.g. 'Python developer'): " KEYWORDS
read -p "📍 Location (e.g. 'London', blank=remote):  " LOCATION
read -p "🏢 Industry for startup search:             " INDUSTRY
INDUSTRY=${INDUSTRY:-"tech startup"}
read -p "⏱  Check every X minutes (default 30):      " INTERVAL
INTERVAL=${INTERVAL:-30}

echo ""
read -p "🆔 Adzuna App ID (get free at adzuna.com): " ADZUNA_ID
read -p "🔑 Adzuna App Key:                          " ADZUNA_KEY
read -p "🗺  Google Maps API key (optional, Enter to skip): " MAPS_KEY

echo -e "\n${BOLD}Step 2: Logging in to Azure${NC}"
az login --only-show-errors

echo -e "\n${BOLD}Step 3: Creating Azure resources${NC}"

# Create resource group
echo -e "  Creating resource group: ${CYAN}${RESOURCE_GROUP}${NC}"
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --only-show-errors \
  --output none

# Create container registry
echo -e "  Creating container registry: ${CYAN}${REGISTRY_NAME}${NC}"
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$REGISTRY_NAME" \
  --sku Basic \
  --admin-enabled true \
  --only-show-errors \
  --output none

# Get registry credentials
echo -e "  Getting registry credentials..."
REGISTRY_SERVER="${REGISTRY_NAME}.azurecr.io"
REGISTRY_USER=$(az acr credential show --name "$REGISTRY_NAME" --query "username" -o tsv)
REGISTRY_PASS=$(az acr credential show --name "$REGISTRY_NAME" --query "passwords[0].value" -o tsv)

echo -e "\n${BOLD}Step 4: Building and pushing Docker image${NC}"
echo -e "  Building: ${CYAN}${IMAGE_NAME}${NC}"

# Build
docker build -t "${IMAGE_NAME}:latest" . --quiet

# Tag for Azure
docker tag "${IMAGE_NAME}:latest" "${REGISTRY_SERVER}/${IMAGE_NAME}:latest"

# Login to Azure registry
docker login "$REGISTRY_SERVER" \
  --username "$REGISTRY_USER" \
  --password "$REGISTRY_PASS" \
  2>/dev/null

# Push
echo -e "  Pushing to Azure Container Registry..."
docker push "${REGISTRY_SERVER}/${IMAGE_NAME}:latest" --quiet

echo -e "\n${BOLD}Step 5: Deploying to Azure Container Instances${NC}"
echo -e "  ${YELLOW}This is where your agent will run 24/7${NC}"

# Delete existing container if it exists
az container delete \
  --resource-group "$RESOURCE_GROUP" \
  --name "$CONTAINER_NAME" \
  --yes \
  --only-show-errors \
  --output none 2>/dev/null || true

# Create Azure File Share for persistent storage
echo -e "  Creating Azure File Share for persistent job data..."
STORAGE_ACCOUNT="jobagentstorage$RANDOM"
az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --only-show-errors --output none

STORAGE_KEY=$(az storage account keys list \
  --account-name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --query "[0].value" -o tsv)

az storage share create \
  --name "jobdata" \
  --account-name "$STORAGE_ACCOUNT" \
  --only-show-errors --output none

# Create the container
az container create \
  --azure-file-volume-account-name "$STORAGE_ACCOUNT" \
  --azure-file-volume-account-key "$STORAGE_KEY" \
  --azure-file-volume-share-name "jobdata" \
  --azure-file-volume-mount-path /mnt/azurefile \
  --resource-group "$RESOURCE_GROUP" \
  --name "$CONTAINER_NAME" \
  --image "${REGISTRY_SERVER}/${IMAGE_NAME}:latest" \
  --registry-login-server "$REGISTRY_SERVER" \
  --registry-username "$REGISTRY_USER" \
  --registry-password "$REGISTRY_PASS" \
  --os-type Linux \
  --cpu 1 \
  --memory 1.5 \
  --restart-policy Always \
  --environment-variables \
    ANTHROPIC_API_KEY="$ANTHROPIC_KEY" \
    NOTIFY_EMAIL_FROM="$EMAIL_FROM" \
    NOTIFY_EMAIL_TO="$EMAIL_TO" \
    NOTIFY_EMAIL_PROVIDER="$EMAIL_PROVIDER" \
    ADZUNA_APP_ID="$ADZUNA_ID" \
    ADZUNA_APP_KEY="$ADZUNA_KEY" \
    GOOGLE_MAPS_API_KEY="${MAPS_KEY:-}" \
    DATA_DIR=/mnt/azurefile \
    SEARCH_KEYWORDS="$KEYWORDS" \
    SEARCH_LOCATION="$LOCATION" \
    SEARCH_INDUSTRY="$INDUSTRY" \
    CHECK_INTERVAL_MINUTES="$INTERVAL" \
  --secure-environment-variables \
    NOTIFY_EMAIL_PASSWORD="$EMAIL_PASS" \
  --only-show-errors \
  --output none

echo -e "\n${GREEN}${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║         ✅ DEPLOYMENT SUCCESSFUL!                    ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════╝${NC}\n"

echo -e "  ${BOLD}Container:${NC}  ${CONTAINER_NAME}"
echo -e "  ${BOLD}Region:${NC}     ${LOCATION}"
echo -e "  ${BOLD}Keywords:${NC}   ${KEYWORDS}"
echo -e "  ${BOLD}Alerts to:${NC}  ${EMAIL_TO}"
echo -e "  ${BOLD}Interval:${NC}   Every ${INTERVAL} minutes\n"

echo -e "  ${CYAN}📧 A test email is being sent to ${EMAIL_TO}${NC}"
echo -e "  ${CYAN}   Check your inbox to confirm it's working!${NC}\n"

echo -e "${BOLD}Useful commands:${NC}"
echo -e "  View live logs:   ${CYAN}az container logs -g ${RESOURCE_GROUP} -n ${CONTAINER_NAME} --follow${NC}"
echo -e "  Check status:     ${CYAN}az container show -g ${RESOURCE_GROUP} -n ${CONTAINER_NAME} --query instanceView.state${NC}"
echo -e "  Stop agent:       ${CYAN}az container stop -g ${RESOURCE_GROUP} -n ${CONTAINER_NAME}${NC}"
echo -e "  Restart agent:    ${CYAN}az container start -g ${RESOURCE_GROUP} -n ${CONTAINER_NAME}${NC}"
echo -e "  Delete all:       ${CYAN}az group delete -n ${RESOURCE_GROUP} --yes${NC}\n"

echo -e "${YELLOW}💰 Estimated cost: ~\$15-20/month for 24/7 operation (1 CPU, 1.5GB RAM)${NC}"
echo -e "${YELLOW}   Free Azure credit: \$200 for new accounts at azure.microsoft.com/free${NC}\n"
