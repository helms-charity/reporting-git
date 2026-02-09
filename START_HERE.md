# 🚀 GitHub Repository User Activity Reporter

**Get your first report in 5 minutes!**

Track GitHub activity within specific repositories: PRs merged, code reviews, issues, commits, and more. Perfect for sprint reports and team dashboards.

## ⚡ Quick Setup (3 Steps)

### Step 1: Install

```bash
cd /Users/chelms/IdeaProjects/reporting-git
pip install -r requirements.txt
```

### Step 2: GitHub Token

```bash
# Get token at: https://github.com/settings/tokens
# Public repos: no scopes needed
# Private repos: select "repo" scope

# Add to ~/.zshenv
export GITHUB_TOKEN="github_pat_xxxxxxxxxxxxx"

# Reload
source ~/.zshenv
```

**Using both github.com and GitHub Enterprise?** Use two tokens and set the Enterprise API URL. Scripts that target Enterprise (e.g. `generate_weekly_reports_excat-plugin.sh`) will use these when set:

```bash
# github.com (idfc, etc.)
export GITHUB_TOKEN="github_pat_xxxxxxxxxxxxx"

# GitHub Enterprise (e.g. Adobe repos) — get URL from your org (e.g. https://github.corp.adobe.com/api/v3)
# export GITHUB_API_URL="https://your-enterprise-host/api/v3"
export GITHUB_ENTERPRISE_TOKEN="your_enterprise_token"
```

### Step 3: Generate Your First Report

```bash
# Single user report
python github_repo_user_report.py aemsites idfc YOUR_USERNAME \
    --days 7 \
    --format html \
    --output reports/team/YOUR_USERNAME-idfc-2026-02-02.html \
    --token $GITHUB_TOKEN

# View it
open reports/team/YOUR_USERNAME-idfc-2026-02-02.html
```

**Done!** 🎉

---

## 📊 Team Reports (Most Common Use Case)

### Create a Repository Script

Create `generate_weekly_reports_idfc.sh`:

```bash
#!/bin/zsh

# Load environment variables
[[ -f ~/.zshrc ]] && source ~/.zshrc

set -e

REPO_OWNER="aemsites"
REPO_NAME="idfc"
DATE=$(date +%Y-%m-%d)
OUTPUT_DIR="reports/team"

USERS=(
    "helms-charity"
    "teammate1"
    "teammate2"
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

wait
echo "✅ All reports completed!"

python generate_team_index.py
echo "✓ Team index: reports/index.html"
```

### Run It

```bash
chmod +x generate_weekly_reports_idfc.sh
./generate_weekly_reports_idfc.sh
open reports/index.html
```

---

## 🎨 What You Get

### Individual Reports
- PRs merged with size distribution (XS-XXL)
- Code reviews given
- Issues opened/closed
- Issue comments
- Commits and code changes

### Team Dashboard (`reports/index.html`)
- **Summary by User**: Total PRs across all repos
- **Individual Reports**: Detailed per-user, per-repo breakdown
- Clickable links to full reports

---

## 🔧 Configuration

### Real Names (Optional)

Create `user_names.json`:

```json
{
  "helms-charity": "Charity Helms",
  "teammate1": "John Doe"
}
```

### File Naming

Follow this pattern for team index to work:
```
reports/team/username-repo_name-yyyy-mm-dd.html
```

---

## 📅 Custom Date Ranges

```bash
# Last 7 days ending on Feb 2
python github_repo_user_report.py aemsites idfc USERNAME \
    --days 7 --startdate 2026-02-02

# Last 30 days ending on Jan 31
python github_repo_user_report.py aemsites idfc USERNAME \
    --days 30 --startdate 2026-01-31
```

---

## 🆘 Common Issues

**"GITHUB_TOKEN not set"**
```bash
export GITHUB_TOKEN="your_token"
source ~/.zshenv
```

**"Rate limit exceeded"**  
→ Use a GitHub token (Step 2 above)

**"No events found"**  
→ Try `--days 30` for longer period

**Private repos not accessible**  
→ Token needs `repo` scope

---
### run a new week's report
1. create new folder (such as 2026-02-02) for last week's reports under /reports
2. move the index file and /team folder into that new dated folder
3. Now there's no files under /reports and you can run a new one.
4. view them in local browser file:///Users/chelms/IdeaProjects/reporting-git/reports/index.html
5. Then do a new push to github for everyone else to see via https://raw.githack.com/helms-charity/reporting-git/main/reports/index.html

## 🤖 Automate It

Add to crontab (runs every Monday at 9 AM):
```bash
crontab -e
# Add:
0 7 * * 1 cd /Users/chelms/IdeaProjects/reporting-git && ./generate_weekly_reports_excat-plugin.sh
0 8 * * 1 cd /Users/chelms/IdeaProjects/reporting-git && ./generate_weekly_reports_extweb-academy.sh
0 9 * * 1 cd /Users/chelms/IdeaProjects/reporting-git && ./generate_weekly_reports_idfc.sh
```

---

## 📖 Need More Details?

See **[README.md](README.md)** for:
- Complete command-line options
- All output formats (text, JSON)
- Multiple repository examples
- GitHub Actions automation
- Troubleshooting guide
- API details

---

## 🎯 Quick Reference

```bash
# Generate single report
python github_repo_user_report.py OWNER REPO USERNAME --days 7 --format html

# Generate team dashboard
./generate_weekly_reports_idfc.sh

# View results
open reports/index.html
```

---

**Happy reporting! 📊✨**

For complete documentation, see [README.md](README.md)
