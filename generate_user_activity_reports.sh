#!/bin/zsh
# Run generate_user_activity_reports.py with GitHub credentials from your environment.
#
# Prefer export in ~/.zshenv so every tool sees them. This script re-exports common vars if set:
#   export GITHUB_TOKEN / GITHUB_API_URL / GITHUB_ENTERPRISE_TOKEN

set -e

[[ -f ~/.zshenv ]] && source ~/.zshenv
# Non-interactive zsh has no compdef until compinit; ~/.zshrc may source plugins that call compdef.
if [[ -f ~/.zshrc ]]; then
    compdef() { :; }
    source ~/.zshrc
fi

# Subprocesses (python) only inherit exported variables. ~/.zshenv often assigns
# without export — export here when set so python sees them (github.com + enterprise).
[[ -n "$GITHUB_TOKEN" ]] && export GITHUB_TOKEN

cd "$(dirname "$0")"

if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️  GITHUB_TOKEN is not set after sourcing ~/.zshenv and ~/.zshrc." >&2
    echo "   Add: export GITHUB_TOKEN=\"your_token\"" >&2
    echo "   Or run: GITHUB_TOKEN=\"your_token\" $0" >&2
    exit 1
fi

# Optional: fix the reporting window (see generate_user_activity_reports.py --help).
#
#   --startdate YYYY-MM-DD   = END date of the window (last day included), not the first day.
#   --days N                 = length of the lookback (default 7).
#
# Example: 7 calendar days ending on 2026-04-10 (inclusive):
#   ./generate_user_activity_reports.sh --startdate 2026-04-10 --days 7
#
# Omit --startdate: events cutoff and per-repo reports both use the current instant in UTC as
# the window end (github_repo_user_report analyzes with end_date = now UTC).
#
# With --startdate: that YYYY-MM-DD is the last UTC calendar day of the window; the first day is
# (--startdate minus --days), matching the public-events cutoff in generate_user_activity_reports.py.
# Issue/PR Search qualifiers use the same UTC day bounds, so metric cards align with repo discovery.
#
# Pass more flags after the script name, e.g. --days 14 --users meejain --startdate 2026-04-10
python generate_user_activity_reports.py \
    --from-user-names \
    --repos-from-events \
    --days 7 \
    "$@"
