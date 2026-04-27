# 🚀 GitHub Repository User Activity Reporter
RULES
- ./generate_user_activity_reports.sh can only get a user's public github repo info.
- for private repos, need to add users to (and run) a separate script for that repo, .generate_weekly_reports_sitescop.sh 
- Same goes for _adobe internal usernames. I would need each user's PAT in order to see their stuff.
- So, I'd have to go to a user's profile page to see what they have contributed to, or just ask them.

**Get your first report in 5 minutes!**

Track GitHub activity within specific repositories: PRs merged, code reviews, issues, commits, and more. Perfect for sprint reports and team dashboards.
- Move last week's files into a new folder with date
- If there are pages migrated, add those to the weekly reports.sh scripts first
- then run the weekly to see what people worked on in public github.com repos:
./generate_user_activity_reports.sh --startdate 2026-04-27 --days 7

- Next run individual weekly reports.sh per known private repos on github.com (such as IDFC).
/.generate_weekly_reports_fondationsap.sh --startdate 2026-04-27 --days 7
/.generate_weekly_reports_idfc.sh --startdate 2026-04-27 --days 7

- delete any individual reports that are all 0's, and delete any that are non-related repos.
- Go to each person's enterprise git profile to see if they worked on something in the past week
https://github.com/meejain_adobe?tab=overview&from=2026-04-20&to=2026-04-27
https://github.com/dfink_adobe?tab=overview&from=2026-04-20&to=2026-04-27
https://github.com/asthabharga_adobe?tab=overview&from=2026-04-06&to=2026-04-13

./generate_weekly_reports_excat.sh --startdate 2026-04-27 --days 7
./generate_weekly_reports_growth-lab.sh --startdate 2026-04-27 --days 7
./generate_weekly_reports_ue-extensions.sh --startdate 2026-04-27 --days 7


- then run individual weekly reports.sh on the repos they have had activity in.
- If any show all 0's due to permissions, then check my fine-grained token if I've added that repo. I may have to add their PR numbers manually to the report if all else fails.

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
# export GITHUB_API_URL="https://api.github.com"
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

Create `user_names.json` (real name first; `github.com` vs `enterprise` per login):

```json
{
  "schema_version": 1,
  "people": [
    {
      "name": "John Doe",
      "accounts": [{ "login": "teammate1", "host": "github.com" }]
    }
  ]
}
```

### File Naming

Follow this pattern for team index to work:
```
reports/team/username-repo_name-yyyy-mm-dd.html
```

Multi-repo runs from `generate_user_activity_reports.py` use:
```
reports/team/username-owner-repo_name-yyyy-mm-dd.html
```
The index parser reads owner/repo from the HTML body, not only the filename.

### Multi-repo orchestration (optional)

Generate reports for every `(login, repo)` from `user_names.json` with a JSON ledger under `reports/user_activity/`.

**Public events only (no `repos_allowlist.json`):** same repo discovery as `list_repos_from_user_events.py`:

```bash
export GITHUB_TOKEN=...
export GITHUB_API_URL=...   # if you have Enterprise accounts in user_names.json
export GITHUB_ENTERPRISE_TOKEN=...
python generate_user_activity_reports.py --from-user-names --repos-from-events --days 7
```

**Allowlist / API discovery** instead: use `--repos-config repos_allowlist.json` (see `repos_allowlist.example.json`). See README for `--max-repos`, rate limits, and tokens.

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
