#!/bin/bash
# AI Daily Report Generator
# Robust wrapper for daily report generation

set -e

REPORT_DIR="/root/clawd/ai-daily-report"
DATE=$(date +%Y-%m-%d)
LOG_FILE="/tmp/ai-daily-report-${DATE}.log"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "[$(date)] Starting AI Daily Report generation for ${DATE}..."

cd "$REPORT_DIR"

# Step 1: Fetch sources
echo "[$(date)] Step 1: Fetching sources..."
python3 scripts/fetch_sources.py || echo "Warning: fetch_sources.py failed, continuing..."

# Step 2: Generate daily.json using AI
echo "[$(date)] Step 2: Generating daily.json..."
# The AI will read the prompt and generate the JSON

# Step 3: Validate JSON
echo "[$(date)] Step 3: Validating JSON..."
python3 scripts/validate_json.py

# Step 4: Render HTML
echo "[$(date)] Step 4: Rendering HTML..."
python3 scripts/render.py

# Step 5: Verify
echo "[$(date)] Step 5: Running verification..."
bash scripts/verify.sh "$DATE"

# Step 6: Commit and push
echo "[$(date)] Step 6: Committing and pushing..."
git add -A
git commit -m "AI日报 ${DATE}" || echo "Nothing to commit"
git push || echo "Push failed or nothing to push"

echo "[$(date)] AI Daily Report generation completed!"
