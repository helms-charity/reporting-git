# Shared CLI parsing for generate_weekly_reports_*.sh
# Usage (from each weekly script, after set -e):
#   PROGNAME="${0##*/}"
#   source "$(dirname "$0")/weekly_report_parse_args.sh"
#   weekly_report_parse_args "$@"

: "${PROGNAME:=weekly_report}"
WEEKLY_REPORT_LIB_DIR="$(cd "$(dirname "$0")" && pwd)"

weekly_report_usage() {
    echo "Usage: $PROGNAME [--startdate YYYY-MM-DD] [--days N]" >&2
    echo "  --startdate   Last UTC calendar day of the window (default: today UTC)" >&2
    echo "  --days        Number of full UTC calendar days (default: 7)" >&2
    exit "${1:-1}"
}

weekly_report_parse_args() {
    DATE=$(date -u +%Y-%m-%d)
    DAYS=7

    while [ $# -gt 0 ]; do
        case "$1" in
            --startdate)
                [ -n "${2:-}" ] || weekly_report_usage
                DATE="$2"
                shift 2
                ;;
            --days)
                [ -n "${2:-}" ] || weekly_report_usage
                DAYS="$2"
                shift 2
                ;;
            -h|--help)
                weekly_report_usage 0
                ;;
            *)
                echo "Unknown option: $1" >&2
                weekly_report_usage
                ;;
        esac
    done

    if ! [[ "$DAYS" == <-> ]] || (( DAYS < 1 )); then
        echo "Error: --days must be a positive integer (got '$DAYS')" >&2
        weekly_report_usage
    fi
    if ! [[ "$DATE" =~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' ]]; then
        echo "Error: --startdate must be YYYY-MM-DD (got '$DATE')" >&2
        weekly_report_usage
    fi
}

# Counts pages migrated in the report window by looking for a
# page-migrations/YYYY-MM-DD/ directory (via the GitHub API) whose date falls
# in [DATE - DAYS + 1, DATE], and counting CSV data rows inside it.
# Uses GITHUB_API_URL/GITHUB_ENTERPRISE_TOKEN if set, else GITHUB_TOKEN.
# Usage: PAGES_MIGRATED=$(weekly_report_pages_migrated "$REPO_OWNER" "$REPO_NAME" "$DATE" "$DAYS")
weekly_report_pages_migrated() {
    local owner="$1" repo="$2" startdate="$3" days="$4"
    local args=(--startdate "$startdate" --days "$days")

    if [ -n "$GITHUB_API_URL" ]; then
        args+=(--api-url "$GITHUB_API_URL")
    fi
    if [ -n "$GITHUB_API_URL" ] && [ -n "$GITHUB_ENTERPRISE_TOKEN" ]; then
        args+=(--token "$GITHUB_ENTERPRISE_TOKEN")
    elif [ -n "$GITHUB_TOKEN" ]; then
        args+=(--token "$GITHUB_TOKEN")
    fi

    python "$WEEKLY_REPORT_LIB_DIR/get_pages_migrated.py" "$owner" "$repo" "${args[@]}"
}
