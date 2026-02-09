#!/bin/zsh
# weekly_report_parallel.sh - Generate reports for multiple users in parallel
# This version runs all user reports simultaneously to reduce total execution time
#
# This repo is on GitHub Enterprise. Set BOTH:
# https://wiki.corp.adobe.com/display/git/GHEC+Authorizing+SSH+Keys+and+Tokens+for+SSO
#   export GITHUB_API_URL="https://your-enterprise-host/api/v3"
#   export GITHUB_ENTERPRISE_TOKEN="your_enterprise_personal_access_token"
#
# Optional: also set GITHUB_TOKEN for github.com repos (other scripts use it).

set -e  # Exit on error

REPO_OWNER="Adobe-AEM-Foundation"
REPO_NAME="aem-exact-plugin"
DATE=$(date +%Y-%m-%d)
OUTPUT_DIR="reports/team"

# Array of usernames to generate reports for
USERS=(
    "dfink_adobe"
    "meejain_adobe"
)

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Check for Enterprise API URL and token (this repo is on GitHub Enterprise)
if [ -z "$GITHUB_API_URL" ] || [ -z "$GITHUB_ENTERPRISE_TOKEN" ]; then
    echo "⚠️  WARNING: This script needs GitHub Enterprise credentials."
    echo "   export GITHUB_API_URL=\"https://your-enterprise-host/api/v3\""
    echo "   export GITHUB_ENTERPRISE_TOKEN=\"your_enterprise_token\""
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
    
    # Run sequentially (no & at end). Use Enterprise API URL and token when set.
    CMD=(python github_repo_user_report.py "$REPO_OWNER" "$REPO_NAME" "$user" --days 7 --format html --output "$OUTPUT_FILE")
    if [ -n "$GITHUB_API_URL" ]; then
        CMD+=(--api-url "$GITHUB_API_URL")
    fi
    if [ -n "$GITHUB_API_URL" ] && [ -n "$GITHUB_ENTERPRISE_TOKEN" ]; then
        CMD+=(--token "$GITHUB_ENTERPRISE_TOKEN")
    elif [ -n "$GITHUB_TOKEN" ]; then
        CMD+=(--token "$GITHUB_TOKEN")
    fi
    "${CMD[@]}"
    
    echo "✓ Completed: @${user}"
    
    # Small delay between users to be respectful to GitHub API
    sleep 2
done

echo ""
echo "---"
echo "📋 Generating team index..."
python generate_team_index.py
echo "✓ Team index: reports/index.html"

echo ""
echo "✅ Done! Generated ${#USERS[@]} reports."
echo "View the team index at: file://$(pwd)/reports/index.html"

