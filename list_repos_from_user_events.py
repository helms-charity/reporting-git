#!/usr/bin/env python3
"""
Walk every account in user_names.json, fetch recent public events, keep only
PullRequestEvent and IssuesEvent, and collect unique owner/repo
names from the last N days (default 7).

Writes a sorted list of owner/repo strings to a temp file (default:
temp_repositories_from_events.txt in the project root).

Requires:
  - github.com accounts: GITHUB_TOKEN (recommended; unauthenticated is heavily limited)
  - enterprise accounts: GITHUB_ENTERPRISE_TOKEN (or GITHUB_TOKEN if that is your
    Enterprise PAT) and GITHUB_API_URL (e.g. https://github.company.com/api/v3)

GitHub returns at most ~300 events per user; very active users may not have a
full 7-day history in the feed.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

from user_events_repos import (
    INCLUDED_EVENT_TYPES,
    collect_repos_from_events,
    cutoff_for_report_window,
    fetch_events_for_user,
    resolve_token_and_base,
)


def load_people(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    people = data.get("people")
    if not isinstance(people, list):
        raise SystemExit(f"Expected 'people' array in {path}")
    return people


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user-names",
        type=Path,
        default=Path(__file__).resolve().parent / "user_names.json",
        help="Path to user_names.json",
    )
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days (default: 7)")
    parser.add_argument(
        "--startdate",
        type=str,
        help="End date of window YYYY-MM-DD (default: today UTC). Aligns with report --startdate.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "temp_repositories_from_events.txt",
        help="Output file (one owner/repo per line)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Per-account stderr details")
    args = parser.parse_args()

    startdate = args.startdate or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cutoff = cutoff_for_report_window(startdate, args.days)

    people = load_people(args.user_names)
    all_repos: Set[str] = set()

    print(f"Window: {args.days} days ending {startdate} (since {cutoff.isoformat()})", file=sys.stderr)
    print(f"Including only event types: {sorted(INCLUDED_EVENT_TYPES)}", file=sys.stderr)
    print("", file=sys.stderr)

    for person in people:
        name = person.get("name", "?")
        accounts = person.get("accounts") or []
        for acc in accounts:
            login = acc.get("login")
            host = acc.get("host", "github.com")
            if not login:
                continue
            try:
                api_base, token = resolve_token_and_base(host)
            except ValueError as e:
                print(f"SKIP {login} ({name}): {e}", file=sys.stderr)
                continue
            if not token and host == "github.com":
                print(
                    f"  [{login}] WARNING: GITHUB_TOKEN not set — rate limit 60/hr",
                    file=sys.stderr,
                )
            if not token and host == "enterprise":
                print(f"SKIP {login}: no GITHUB_ENTERPRISE_TOKEN or GITHUB_TOKEN", file=sys.stderr)
                continue

            if args.verbose:
                print(f"Fetching events: {login} ({host}) …", file=sys.stderr)
            events = fetch_events_for_user(login, api_base, token, cutoff)
            included = [e for e in events if (e.get("type") or "") in INCLUDED_EVENT_TYPES]
            repos, type_counts = collect_repos_from_events(events)
            all_repos |= repos
            print(
                f"  {login}: {len(events)} events in window, "
                f"{len(included)} matching PR/Issue types → {len(repos)} repo(s)",
                file=sys.stderr,
            )
            if args.verbose and type_counts:
                print(f"    types: {dict(sorted(type_counts.items()))}", file=sys.stderr)

    lines = sorted(all_repos, key=str.lower)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    print("", file=sys.stderr)
    print(f"Unique owner/repos (all accounts): {len(all_repos)}", file=sys.stderr)
    print(f"Wrote: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
