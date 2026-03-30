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

# Default matches START_HERE; pass extra args after the script name, e.g. --days 14 --users meejain
python generate_user_activity_reports.py \
    --from-user-names \
    --repos-from-events \
    --days 7 \
    "$@"
