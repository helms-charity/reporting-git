# GitHub Repository User Activity Reporter

Generate weekly or monthly reports of a GitHub user's activity in a specific repository, including pull requests, code reviews, issues, and more.

## Features

Repository-specific reports with comprehensive metrics:
- 📊 **Pull Requests** - Track PRs merged with detailed stats (additions, deletions, files changed)
- 📏 **PR Size Distribution** - Categorize PRs by size (XS, S, M, L, XL, XXL) like [OSSInsight](https://ossinsight.io/)
- 👀 **Code Reviews** - Monitor reviews given with approval status
- 🐛 **Issues Opened** - Track new issues created
- ✅ **Issues Closed** - Track issues closed by the user
- 💬 **Issue Comments** - See all comments made on issues with previews
- 💾 **Commits** - Track commits in PRs and direct commits
- 📈 **Lines Added/Deleted** - Full code change tracking

## Additional Features

- 📅 **Flexible Time Ranges** - Analyze activity from the last 7-90 days
- 🎨 **Multiple Output Formats** - Text, HTML, or JSON reports
- 🚀 **GitHub API Integration** - Uses official GitHub REST API (no external dependencies)
- 📊 **Beautiful HTML Reports** - Modern, interactive reports with charts and metrics
- 🤖 **Automation Ready** - Perfect for CI/CD pipelines and scheduled reports

## Installation

```bash
# Clone or download this repository
cd reporting-git

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
# Basic usage (text output to terminal)
python github_repo_user_report.py aemsites idfc helms-charity --days 7

# Weekly HTML report with all metrics
python github_repo_user_report.py aemsites idfc helms-charity --days 7 --format html --output ~/IdeaProjects/reporting-git/reports/weekly.html

# Monthly HTML report
python github_repo_user_report.py aemsites idfc helms-charity --days 30 --format html --output ~/IdeaProjects/reporting-git/reports/monthly.html

# JSON for automation
python github_repo_user_report.py aemsites idfc helms-charity --days 7 --format json --output report.json
```

### Using a GitHub Token (Highly Recommended)

GitHub API has rate limits. Using a personal access token increases your rate limit from 60 to 5000 requests/hour.

1. **Create a token**: Go to [GitHub Settings > Developer Settings > Personal Access Tokens](https://github.com/settings/tokens)
2. **No special permissions needed** for public data
3. **Use the token**:

```bash
# Option 1: Environment variable (recommended)
export GITHUB_TOKEN=github_pat_xxxxxxxxxxxxx
python github_repo_user_report.py aemsites idfc helms-charity --days 7

# Option 2: Command line argument
python github_repo_user_report.py aemsites idfc helms-charity --days 7 --token github_pat_xxxxxxxxxxxxx
```

## Command Line Options

```
usage: github_repo_user_report.py [-h] [--days DAYS] [--format {text,html,json}]
                                  [--output OUTPUT] [--token TOKEN]
                                  owner repo username

positional arguments:
  owner                 Repository owner (e.g., 'aemsites')
  repo                  Repository name (e.g., 'idfc')
  username              GitHub username to analyze

optional arguments:
  --days DAYS          Number of days to analyze (default: 7)
  --format {text,html,json}
                       Output format (default: text)
  --output OUTPUT, -o OUTPUT
                       Output file (default: stdout)
  --token TOKEN        GitHub personal access token
```

## Output Formats

### Text Format (Default)
Perfect for terminal output and quick summaries:
```bash
python github_repo_user_report.py aemsites idfc helms-charity --days 7
```

### HTML Format (Recommended for Reports)
Beautiful, interactive reports with modern UI:
```bash
python github_repo_user_report.py aemsites idfc helms-charity --days 30 --format html -o report.html
open report.html
```

### JSON Format (For Automation)
Machine-readable format for further processing:
```bash
python github_repo_user_report.py aemsites idfc helms-charity --format json -o report.json
```

## Examples

### Weekly Team Summary
```bash
#!/bin/bash
# weekly_report.sh - Generate reports for your team in a specific repository

REPO_OWNER="aemsites"
REPO_NAME="idfc"

for user in "helms-charity" "teammate1" "teammate2"; do
    python github_repo_user_report.py "$REPO_OWNER" "$REPO_NAME" "$user" \
        --days 7 \
        --format html \
        --output "reports/${user}-weekly.html"
done
```

### Monthly Personal Report
```bash
REPO_OWNER="aemsites"
REPO_NAME="idfc"
python github_repo_user_report.py "$REPO_OWNER" "$REPO_NAME" helms-charity \
    --days 30 \
    --format html \
    --output ~/IdeaProjects/reporting-git/reports/my-monthly-github-activity.html
```

## Use Cases

This tool is perfect for:
- ✅ Tracking work on a **specific repository**
- ✅ **Sprint retrospectives** and **project reports**
- ✅ **Performance reviews** with detailed metrics
- ✅ Team activity **monitoring and dashboards**
- ✅ **Weekly/monthly** status reports
- ✅ CI/CD **automation and notifications**

## Comparison with OSSInsight

| Feature | OSSInsight | This Tool |
|---------|-----------|-----------|
| **Time Range** | All-time history | Recent (7-90 days) |
| **Focus** | Repository-wide stats | Individual user activity in a repo |
| **PR Size Distribution** | ✅ | ✅ |
| **Issue Tracking** | ❌ | ✅ (Opens + Closes + Comments) |
| **Code Reviews** | Limited | ✅ Full review history |
| **Data Source** | GH Archive | GitHub API (real-time) |
| **Setup** | Web-based | Command-line |
| **Customization** | Limited | Fully customizable |
| **Automation** | ❌ | ✅ (CLI, cron, CI/CD) |

## Data Sources

This tool uses the **GitHub Search and Repository APIs** which provide:
- Real-time data (no delay)
- Comprehensive activity tracking
- PR details including size, commits, and files changed
- Full review history with approval status
- Issue creation, closure, and comments
- Direct commit tracking

## Automation

### Cron Job (Weekly Reports)
```bash
# Edit crontab
crontab -e

# Add this line to generate reports every Monday at 9 AM
0 9 * * 1 cd ~/reporting-git && python github_repo_user_report.py aemsites idfc helms-charity --days 7 --format html --output ~/IdeaProjects/reporting-git/reports/weekly-report.html
```

### GitHub Actions (Automated Reports)
Create `.github/workflows/weekly-report.yml`:
```yaml
name: Weekly GitHub Activity Report

on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday at 9 AM
  workflow_dispatch:

jobs:
  generate-report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: python github_repo_user_report.py aemsites idfc helms-charity --days 7 --format html --output report.html
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      - uses: actions/upload-artifact@v3
        with:
          name: weekly-report
          path: report.html
```

## 🎓 Learning Resources

- [GitHub Events API Documentation](https://docs.github.com/en/rest/activity/events)
- [GitHub Event Types](https://docs.github.com/en/rest/using-the-rest-api/github-event-types)
- [OSSInsight API](https://ossinsight.io/docs/api)
- [GH Archive](https://www.gharchive.org/)

## Troubleshooting

### Rate Limit Errors
```
Error: 403 - Rate limit exceeded
```
**Solution**: Use a GitHub token (see Usage section above)

### No Events Found
```
No events found for @username in the last 7 days
```
**Possible causes**:
- User has no public activity
- User's activity is older than the specified days
- Username is incorrect

### Empty Statistics
The GitHub Events API only returns the last 300 events. For very active users, events older than a few days may not be available.

## License

MIT License - Feel free to modify and use for your needs!

## Contributing

Contributions welcome! Feel free to:
- Add new metrics
- Improve the HTML report design
- Add more output formats
- Optimize API calls

