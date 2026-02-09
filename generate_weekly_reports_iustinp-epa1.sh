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

REPO_OWNER="iustinp"
REPO_NAME="iustinp-epa1"
DATE=$(date +%Y-%m-%d)
OUTPUT_DIR="reports/team"

# Array of usernames to generate reports for
USERS=(
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

echo "🚀 Starting report generation for ${#USERS[@]} users..."
echo "Repository: $REPO_OWNER/$REPO_NAME"
echo "Date: $DATE"
echo "---"

# Start all reports sequentially (to avoid rate limiting)
for user in "${USERS[@]}"; do
    OUTPUT_FILE="${OUTPUT_DIR}/${user}-${REPO_NAME}-${DATE}.html"
    
    echo "Starting report for @${user}..."
    
    # Run sequentially (no & at end)
    if [ -n "$GITHUB_TOKEN" ]; then
        python github_repo_user_report.py "$REPO_OWNER" "$REPO_NAME" "$user" \
            --days 7 \
            --format html \
            --token "$GITHUB_TOKEN" \
            --output "$OUTPUT_FILE"
    else
        python github_repo_user_report.py "$REPO_OWNER" "$REPO_NAME" "$user" \
            --days 7 \
            --format html \
            --output "$OUTPUT_FILE"
    fi
    
    echo "✓ Completed: @${user}"
    
    # Small delay between users to be respectful to GitHub API
    sleep 2
done

echo "✅ All reports completed!"

echo ""
echo "---"
echo "📋 Generating team index..."
python generate_team_index.py
echo "✓ Team index: reports/index.html"

echo ""
echo "✅ Done! Generated ${#USERS[@]} reports in parallel."
echo "View the team index at: file://$(pwd)/reports/index.html"

