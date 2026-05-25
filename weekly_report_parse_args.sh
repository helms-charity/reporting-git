# Shared CLI parsing for generate_weekly_reports_*.sh
# Usage (from each weekly script, after set -e):
#   PROGNAME="${0##*/}"
#   source "$(dirname "$0")/weekly_report_parse_args.sh"
#   weekly_report_parse_args "$@"

: "${PROGNAME:=weekly_report}"

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
