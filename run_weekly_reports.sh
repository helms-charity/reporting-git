#!/bin/zsh

set -e

REPO_DIR="/Users/chelms/IdeaProjects/reporting-git"
REPORTS_DIR="$REPO_DIR/reports"

# Most recent Sunday (today counts if today is Sunday)
dow=$(date +%u)                          # 1=Mon .. 7=Sun
offset=$((dow % 7))
MOST_RECENT_SUNDAY=$(date -v-${offset}d +%Y-%m-%d)

# One week earlier - the date the currently-in-place reports were generated with
ARCHIVE_DATE=$(date -j -v-7d -f "%Y-%m-%d" "$MOST_RECENT_SUNDAY" +%Y-%m-%d)

echo "Most recent Sunday: $MOST_RECENT_SUNDAY"
echo "Archive folder date: $ARCHIVE_DATE"

cd "$REPORTS_DIR"

if [[ ! -f index.html ]]; then
    echo "No existing reports/index.html found - skipping archive step."
elif [[ -d "$ARCHIVE_DATE" ]]; then
    echo "reports/$ARCHIVE_DATE already exists - skipping archive step to avoid overwriting it."
else
    echo "Archiving index.html, team, and user_activity into reports/$ARCHIVE_DATE ..."
    mkdir "$ARCHIVE_DATE"
    mv index.html team user_activity "$ARCHIVE_DATE"/
fi

cd "$REPO_DIR"

echo "Running generate_user_activity_reports.sh --startdate $MOST_RECENT_SUNDAY --days 7 ..."
./generate_user_activity_reports.sh --startdate "$MOST_RECENT_SUNDAY" --days 7

echo "Running generate_weekly_reports_excat.sh --startdate $MOST_RECENT_SUNDAY --days 7 ..."
./generate_weekly_reports_excat.sh --startdate "$MOST_RECENT_SUNDAY" --days 7

echo "Running generate_weekly_reports_growth-lab.sh --startdate $MOST_RECENT_SUNDAY --days 7 ..."
./generate_weekly_reports_growth-lab.sh --startdate "$MOST_RECENT_SUNDAY" --days 7

echo ""
echo "Done. Archived previous data (if any) under reports/$ARCHIVE_DATE, generated new reports for $MOST_RECENT_SUNDAY."
echo "Review reports/index.html, then commit and push manually when ready."
