#!/bin/zsh
# weekly_report_parallel.sh - Generate reports for multiple users in parallel
# This version runs all user reports simultaneously to reduce total execution time
#
# IMPORTANT: Set GITHUB_TOKEN environment variable to avoid rate limits
#   export GITHUB_TOKEN="your_github_personal_access_token"
#
# Without a token: 60 requests/hour (may fail with multiple users)
# With a token: 5000 requests/hour (recommended for parallel execution)

set -e  # Exit on error

REPO_OWNER="aemsites"
REPO_NAME="extweb-academy"
DATE=$(date +%Y-%m-%d)
OUTPUT_DIR="reports/team"

# Array of usernames to generate reports for
USERS=(
    "helms-charity"
    "amarghioali"
    "inasplayground"
    "iustinp"
)

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Check for GitHub token
if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️  WARNING: GITHUB_TOKEN not set. You may hit API rate limits."
    echo "   Set it with: export GITHUB_TOKEN=\"your_token\""
    echo "   Get a token at: https://github.com/settings/tokens"
    echo ""
fi

echo "🚀 Starting parallel report generation for ${#USERS[@]} users..."
echo "Repository: $REPO_OWNER/$REPO_NAME"
echo "Date: $DATE"
echo "---"

# Array to store background job PIDs
declare -a PIDS

# Start all reports in parallel
for user in "${USERS[@]}"; do
    OUTPUT_FILE="${OUTPUT_DIR}/${user}-${REPO_NAME}-${DATE}.html"
    
    echo "Starting report for @${user}..."
    
    # Run in background and capture PID
    # Pass token explicitly if set (background jobs inherit env vars, but being explicit is safer)
    if [ -n "$GITHUB_TOKEN" ]; then
        python github_repo_user_report.py "$REPO_OWNER" "$REPO_NAME" "$user" \
            --days 7 \
            --format html \
            --token "$GITHUB_TOKEN" \
            --output "$OUTPUT_FILE" &
    else
        python github_repo_user_report.py "$REPO_OWNER" "$REPO_NAME" "$user" \
            --days 7 \
            --format html \
            --output "$OUTPUT_FILE" &
    fi
    
    PIDS+=($!)
done

echo "---"
echo "⏳ All ${#USERS[@]} reports started in parallel. Waiting for completion..."
echo ""

# Wait for all background jobs to complete
wait

echo "✅ All reports completed!"

echo ""
echo "---"
echo "📋 Generating team index..."
python generate_team_index.py
echo "✓ Team index: reports/index.html"

echo ""
echo "✅ Done! Generated ${#USERS[@]} reports in parallel."
echo "View the team index at: file://$(pwd)/reports/index.html"

