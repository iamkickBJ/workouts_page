#!/bin/bash

# Configuration
PROJECT_DIR="/Users/kick/Documents/Playground/workouts_page"
PYTHON_BIN="/usr/bin/python3"
LOG_FILE="/tmp/garmin_local_sync.log"

# Navigate to project
cd "$PROJECT_DIR" || exit

echo "--- Sync Started: $(date) ---" >> "$LOG_FILE"

# 1. Update project from GitHub (Clean Start)
git pull origin master >> "$LOG_FILE" 2>&1

# 2. Get local 1-year secret (Patched browser UA)
# Assuming iamkick@me.com / Ps3xbox360
SECRET_STRING=$($PYTHON_BIN run_page/get_garmin_secret.py "iamkick@me.com" "Ps3xbox360" | tr -d '\n\r ')

if [ -z "$SECRET_STRING" ]; then
    echo "ERROR: Failed to generate secret string." >> "$LOG_FILE"
    exit 1
fi

# 3. Perform Sync (with browser spoofing patch)
$PYTHON_BIN run_page/garmin_sync.py "$SECRET_STRING" >> "$LOG_FILE" 2>&1

# 4. Git Push Results
git add .
git commit -m "Auto sync from Local Mac Agent ($(date))" >> "$LOG_FILE" 2>&1
git push origin master >> "$LOG_FILE" 2>&1

echo "--- Sync Completed: $(date) ---" >> "$LOG_FILE"
