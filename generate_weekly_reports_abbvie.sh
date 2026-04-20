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

REPO_OWNER="rusmeenkhan1"
REPO_NAME="abbvie"
DATE=$(date +%Y-%m-%d)
OUTPUT_DIR="reports/team"
PAGES_MIGRATED="13"

# Array of usernames to generate reports for
USERS=(
    "rusmeenkhan1"
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

echo "🚀 Starting report generation for ${#USERS[@]} users..."
echo "Repository: $REPO_OWNER/$REPO_NAME"
echo "Date: $DATE"
echo "---"

# Start all reports sequentially (to avoid rate limiting)
REPORTS_OK=0
REPORTS_SKIPPED=0

for user in "${USERS[@]}"; do
    OUTPUT_FILE="${OUTPUT_DIR}/${user}-${REPO_NAME}-${DATE}.html"
    
    echo "Starting report for @${user}..."
    
    # Run sequentially (no & at end). --omit-if-empty: no HTML when all metrics are zero (exit 2).
    set +e
    if [ -n "$GITHUB_TOKEN" ]; then
        python github_repo_user_report.py "$REPO_OWNER" "$REPO_NAME" "$user" \
            --days 7 \
            --format html \
            --token "$GITHUB_TOKEN" \
            --pages-migrated "${PAGES_MIGRATED:-0}" \
            --omit-if-empty \
            --output "$OUTPUT_FILE"
    else
        python github_repo_user_report.py "$REPO_OWNER" "$REPO_NAME" "$user" \
            --days 7 \
            --format html \
            --pages-migrated "${PAGES_MIGRATED:-0}" \
            --omit-if-empty \
            --output "$OUTPUT_FILE"
    fi
    rc=$?
    set -e
    if [ "$rc" -eq 0 ]; then
        echo "✓ Completed: @${user}"
        REPORTS_OK=$((REPORTS_OK + 1))
    elif [ "$rc" -eq 2 ]; then
        echo "○ Skipped @${user} (no measurable activity in window)"
        REPORTS_SKIPPED=$((REPORTS_SKIPPED + 1))
        rm -f "$OUTPUT_FILE"
    else
        exit "$rc"
    fi
    
    # Small delay between users to be respectful to GitHub API
    sleep 2
done

echo ""
echo "---"
echo "📋 Generating team index..."
python generate_team_index.py
echo "✓ Team index: reports/index.html"

echo ""
echo "✅ Done! Wrote ${REPORTS_OK} HTML report(s)."
[ "${REPORTS_SKIPPED:-0}" -gt 0 ] && echo "   Skipped ${REPORTS_SKIPPED} user(s) (no measurable activity in window)."
echo "View the team index at: file://$(pwd)/reports/index.html"

