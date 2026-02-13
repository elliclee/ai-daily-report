#!/bin/bash
# Auto-update TechMeme for AI Daily Report

cd /root/clawd/ai-daily-report

# Fetch and update
python3 scripts/update_techneme.py >> /var/log/techneme-update.log 2>&1

# If there are changes, commit and push
if [ -n "$(git status --porcelain index.html)" ]; then
    git add index.html
    git commit -m "Auto-update TechMeme headlines - $(date +%Y-%m-%d)"
    git push
fi
