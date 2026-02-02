# See the HTML list of reports
https://raw.githack.com/helms-charity/reporting-git/main/reports/index.html
or
https://htmlpreview.github.io/?https://github.com/helms-charity/reporting-git/blob/main/reports/index.html

# GitHub Repository User Activity Reporter

Generate weekly or monthly reports of GitHub user activity within specific repositories, including pull requests, code reviews, issues, and more.

> **🚀 New here?** Start with **[START_HERE.md](START_HERE.md)** for a 5-minute quick start guide!

## Features

Repository-specific reports with comprehensive metrics:
- 📊 **Pull Requests Merged** - Track PRs with detailed stats (additions, deletions, files changed)
- 📏 **PR Size Distribution** - Categorize PRs by size (XS, S, M, L, XL, XXL) like [OSSInsight](https://ossinsight.io/)
- 👀 **Code Reviews** - Monitor reviews given with approval status
- 🐛 **Issues Opened** - Track new issues created
- ✅ **Issues Closed** - Track issues closed by the user
- 💬 **Issue Comments** - See all comments made on issues with previews
- 💾 **Commits** - Track commits in PRs and direct commits
- 📈 **Lines Added/Deleted** - Full code change tracking
- 🏆 **Team Index** - Aggregated team dashboard with individual and summary views

## Additional Features

- 📅 **Flexible Time Ranges** - Analyze activity with custom date ranges (--days and --startdate)
- 🎨 **Multiple Output Formats** - Text, HTML, or JSON reports
- 🚀 **GitHub API Integration** - Uses official GitHub REST API (no external dependencies)
- 📊 **Beautiful HTML Reports** - Modern, interactive reports with charts and metrics
- 🤖 **Automation Ready** - Perfect for CI/CD pipelines and scheduled reports
- ⚡ **Parallel Execution** - Generate reports for multiple users simultaneously

## Installation

```bash
# Clone or download this repository
cd reporting-git

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### 1. Generate a Single User Report

```bash
# Basic usage (text output to terminal)
python github_repo_user_report.py aemsites idfc helms-charity --days 7

# Weekly HTML report
python github_repo_user_report.py aemsites idfc helms-charity --days 7 \
    --format html \
    --output reports/team/helms-charity-idfc-2026-02-02.html

# Monthly HTML report with custom date range
python github_repo_user_report.py aemsites idfc helms-charity \
    --days 30 \
    --startdate 2026-02-02 \
    --format html \
    --output reports/monthly.html

# JSON for automation
python github_repo_user_report.py aemsites idfc helms-charity \
    --days 7 \
    --format json \
    --output report.json
```

### 2. Set Up GitHub Token (Recommended)

GitHub API has rate limits. Using a personal access token increases your rate limit from 60 to 5000 requests/hour.

1. **Create a token**: Go to [GitHub Settings > Developer Settings > Personal Access Tokens](https://github.com/settings/tokens)
2. **For public repositories**: No special permissions needed
3. **For private repositories**: Select the `repo` scope
4. **Use the token**:

```bash
# Option 1: Environment variable (recommended)
export GITHUB_TOKEN="github_pat_xxxxxxxxxxxxx"
python github_repo_user_report.py aemsites idfc helms-charity --days 7

# Option 2: Command line argument
python github_repo_user_report.py aemsites idfc helms-charity \
    --days 7 \
    --token "github_pat_xxxxxxxxxxxxx"
```

**Pro Tip**: Add the export command to your `~/.zshrc` or `~/.zshenv` file for permanent use.

### 3. Generate Team Reports

#### Option A: Create Individual Repository Scripts

Create a script for each repository you want to track:

```bash
#!/bin/zsh
# generate_weekly_reports_idfc.sh

# Load environment variables
[[ -f ~/.zshrc ]] && source ~/.zshrc

set -e

REPO_OWNER="aemsites"
REPO_NAME="idfc"
DATE=$(date +%Y-%m-%d)
OUTPUT_DIR="reports/team"

USERS=(
    "helms-charity"
    "amarghioali"
    "bunting-adbe"
    "iustinp"
)

mkdir -p "$OUTPUT_DIR"

echo "🚀 Starting reports for ${#USERS[@]} users..."

for user in "${USERS[@]}"; do
    OUTPUT_FILE="${OUTPUT_DIR}/${user}-${REPO_NAME}-${DATE}.html"
    echo "Starting report for @${user}..."
    
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
done

# Wait for all reports to complete
wait

echo "✅ All reports completed!"

# Generate team index
python generate_team_index.py
echo "✓ Team index: reports/index.html"
```

Make it executable:
```bash
chmod +x generate_weekly_reports_idfc.sh
```

Run it:
```bash
./generate_weekly_reports_idfc.sh
```

#### Option B: Manual Sequential Generation

```bash
# Generate individual reports
python github_repo_user_report.py aemsites idfc helms-charity --days 7 --format html \
    --output reports/team/helms-charity-idfc-2026-02-02.html

python github_repo_user_report.py aemsites idfc teammate1 --days 7 --format html \
    --output reports/team/teammate1-idfc-2026-02-02.html

python github_repo_user_report.py aemsites idfc teammate2 --days 7 --format html \
    --output reports/team/teammate2-idfc-2026-02-02.html

# Generate the team index
python generate_team_index.py

# Open the index
open reports/index.html
```

### 4. Configure User Real Names

Create a `user_names.json` file in the project root to map GitHub usernames to real names:

```json
{
  "helms-charity": "Charity Helms",
  "amarghioali": "Bogdan Amarghioali",
  "bunting-adbe": "Josh Bunting",
  "teammate1": "Real Name"
}
```

The team index will use these names in the summary table.

## Command-Line Options

```bash
python github_repo_user_report.py OWNER REPO USERNAME [OPTIONS]

Required Arguments:
  OWNER                 Repository owner (e.g., "aemsites")
  REPO                  Repository name (e.g., "idfc")
  USERNAME              GitHub username to analyze (e.g., "helms-charity")

Options:
  --days DAYS           Number of days to analyze (default: 7)
  --startdate DATE      End date for analysis in YYYY-MM-DD format
                        (default: today). Use with --days to specify
                        a custom date range.
  --format FORMAT       Output format: text, html, or json (default: text)
  --output FILE         Output file path (default: stdout for text)
  --token TOKEN         GitHub personal access token
```

## Examples

### Weekly Report for Specific Date Range

```bash
# Get activity from January 26 to February 2 (7 days ending on Feb 2)
python github_repo_user_report.py aemsites idfc helms-charity \
    --days 7 \
    --startdate 2026-02-02 \
    --format html \
    --output reports/weekly-jan26-feb02.html
```

### Monthly Report Ending on Specific Date

```bash
# Get 30 days of activity ending on January 31
python github_repo_user_report.py aemsites idfc helms-charity \
    --days 30 \
    --startdate 2026-01-31 \
    --format html \
    --output reports/monthly-jan.html
```

### Multiple Repositories

```bash
# Generate reports for the same user across different repositories
python github_repo_user_report.py aemsites idfc helms-charity --days 7 \
    --format html --output reports/team/helms-charity-idfc-2026-02-02.html

python github_repo_user_report.py aemsites other-repo helms-charity --days 7 \
    --format html --output reports/team/helms-charity-other-repo-2026-02-02.html

# Generate team index to aggregate
python generate_team_index.py
```

## Team Index

The `generate_team_index.py` script creates an aggregated dashboard at `reports/index.html` that includes:

1. **Summary by User**: Aggregated totals across all repositories
   - Date (most recent report)
   - GitHub username
   - Real name (from `user_names.json`)
   - Total PRs merged across all repos

2. **Individual Reports**: Detailed breakdown per user per repository
   - All metrics from individual reports
   - Clickable links to detailed HTML reports
   - Sorted alphabetically by username

The index automatically scans `reports/team/` for all HTML files matching the pattern `username-repo_name-yyyy-mm-dd.html`.

### Running the Team Index Generator

```bash
# After generating individual reports
python generate_team_index.py

# Open the index
open reports/index.html
```

## Report Output Formats

### Text Output
Quick summaries perfect for terminal use or logging:
```
================================================================================
GitHub Repository Activity Report
Repository: aemsites/idfc
User: @helms-charity
Period: 2026-01-26 to 2026-02-02 (7 days)
================================================================================
...
```

### HTML Output
Beautiful, interactive reports with:
- Modern gradient design
- Metric cards with statistics
- PR size distribution charts
- Detailed tables for PRs, reviews, issues
- Fully responsive (mobile-friendly)
- Dark-themed code blocks

### JSON Output
Structured data for automation:
```json
{
  "user": "helms-charity",
  "repository": "aemsites/idfc",
  "period": {...},
  "stats": {...},
  "pull_requests": [...],
  "reviews": [...],
  "issues": [...]
}
```

## File Naming Convention

For best results with the team index, follow this naming convention for individual reports:

```
reports/team/username-repo_name-yyyy-mm-dd.html
```

Examples:
- `reports/team/helms-charity-idfc-2026-02-02.html`
- `reports/team/amarghioali-extweb-academy-2026-02-02.html`

## Data Sources

This tool uses the GitHub REST API to fetch:
- **Pull Requests**: `/repos/{owner}/{repo}/pulls` and search API
- **Reviews**: `/search/issues?q=reviewed-by:{user}`
- **Issues**: `/search/issues?q=author:{user}` and `/search/issues?q=assignee:{user}`
- **Issue Comments**: `/search/issues?q=commenter:{user}`
- **Commits**: `/repos/{owner}/{repo}/commits?author={user}`

All data is fetched in real-time and not stored locally.

## Rate Limits

| Token Status | Rate Limit | Best For |
|--------------|------------|----------|
| No token | 60 requests/hour | Testing only |
| With token | 5000 requests/hour | Production use |

**Recommendation**: Always use a GitHub token for team reporting and automation.

## Private Repository Access

To access private repositories, your GitHub token must have the `repo` scope:

1. Go to [https://github.com/settings/tokens](https://github.com/settings/tokens)
2. Generate new token (classic)
3. Select **`repo`** (Full control of private repositories)
4. Use the token as described in the Quick Start section

## Troubleshooting

### "⚠️ Warning: No GitHub token provided"
**Solution**: Set your GitHub token:
```bash
export GITHUB_TOKEN="your_token_here"
```

### "403 Forbidden" or "429 Too Many Requests"
**Problem**: Rate limit exceeded  
**Solution**: Use a GitHub token (see Quick Start section)

### "No events found" or empty reports
**Possible causes**:
- User has no activity in the specified time range
- User doesn't have access to the repository
- Token doesn't have the correct permissions (for private repos)

**Solutions**:
- Increase `--days` (e.g., `--days 30`)
- Verify the username and repository name
- For private repos, ensure token has `repo` scope

### Scripts not loading GitHub token (zsh)
**Problem**: `#!/bin/zsh` scripts don't load `~/.zshrc` automatically  
**Solution**: Scripts already include `source ~/.zshrc` at the top. Alternatively, add token to `~/.zshenv` which is loaded for all shells.

## Automation

### Cron Job Example

```bash
# Add to crontab (crontab -e)
# Run every Monday at 9 AM
0 9 * * 1 cd /Users/chelms/IdeaProjects/reporting-git && ./generate_weekly_reports_idfc.sh
```

### GitHub Actions Example

```yaml
name: Weekly Team Reports
on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday at 9 AM
  workflow_dispatch:

jobs:
  generate-reports:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.x'
      - run: pip install -r requirements.txt
      - run: |
          export GITHUB_TOKEN="${{ secrets.GITHUB_TOKEN }}"
          ./generate_weekly_reports_idfc.sh
      - uses: actions/upload-artifact@v3
        with:
          name: weekly-reports
          path: reports/
```

## Project Structure

```
reporting-git/
├── github_repo_user_report.py     # Main report generator
├── generate_team_index.py         # Team index generator
├── user_names.json                # Username to real name mapping
├── requirements.txt               # Python dependencies
├── README.md                      # Complete documentation (this file)
├── START_HERE.md                  # Quick start guide (start here!)
├── reports/
│   ├── index.html                 # Team dashboard (generated)
│   └── team/
│       ├── user1-repo-date.html   # Individual reports
│       ├── user2-repo-date.html
│       └── ...
└── generate_weekly_reports_*.sh   # Repository-specific scripts
```

## Contributing

This is a personal tool, but improvements are welcome! Key areas:
- Additional metrics
- New visualizations
- Performance improvements
- Documentation updates

## License

MIT License - feel free to use and modify for your needs.

## Credits

Inspired by [OSSInsight](https://ossinsight.io/) for PR size distribution and activity tracking concepts.

---

**Happy reporting! 📊✨**
