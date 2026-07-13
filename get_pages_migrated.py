#!/usr/bin/env python3
"""
Count pages migrated in a given report window.

Looks for a `page-migrations/YYYY-MM-DD/` directory (via the GitHub Contents
API) whose date falls inside the report window. If found, counts the data
rows (excluding the header) in any .csv file(s) inside it.

Prints a single integer to stdout (0 if nothing matches or the directory
doesn't exist). Diagnostics go to stderr. Intended to be used from the
generate_weekly_reports_*.sh scripts, e.g.:

    PAGES_MIGRATED=$(python get_pages_migrated.py "$REPO_OWNER" "$REPO_NAME" \
        --startdate "$DATE" --days "$DAYS" --token "$GITHUB_TOKEN")
"""

import argparse
import base64
import csv
import io
import re
import sys

import requests

from user_events_repos import resolve_report_window

DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def list_dir(base_url, headers, owner, repo, path):
    url = f"{base_url}/repos/{owner}/{repo}/contents/{path}"
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    return response.json()


def count_csv_rows(base_url, headers, owner, repo, path):
    url = f"{base_url}/repos/{owner}/{repo}/contents/{path}"
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    entry = response.json()
    content = base64.b64decode(entry["content"]).decode("utf-8", errors="replace")
    rows = [row for row in csv.reader(io.StringIO(content)) if row]
    if not rows:
        return 0

    data_rows = rows[1:]  # exclude header
    return sum(
        1
        for row in data_rows
        if (len(row) > 0 and row[0].strip()) or (len(row) > 1 and row[1].strip())
    )


def count_pages_migrated(base_url, headers, owner, repo, since_day, end_day, path="page-migrations"):
    try:
        entries = list_dir(base_url, headers, owner, repo, path)
    except requests.RequestException as exc:
        print(f"⚠️  Could not list '{path}' for {owner}/{repo}: {exc}", file=sys.stderr)
        return 0

    total = 0
    for entry in entries:
        if entry.get("type") != "dir" or not DATE_DIR_RE.match(entry.get("name", "")):
            continue
        date_str = entry["name"]
        if not (since_day <= date_str <= end_day):
            continue

        try:
            date_entries = list_dir(base_url, headers, owner, repo, entry["path"])
        except requests.RequestException as exc:
            print(f"⚠️  Could not list '{entry['path']}': {exc}", file=sys.stderr)
            continue

        for date_entry in date_entries:
            if date_entry.get("type") != "file" or not date_entry.get("name", "").endswith(".csv"):
                continue
            try:
                total += count_csv_rows(base_url, headers, owner, repo, date_entry["path"])
            except (requests.RequestException, KeyError, UnicodeDecodeError) as exc:
                print(f"⚠️  Could not read '{date_entry['path']}': {exc}", file=sys.stderr)

    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("owner", help="Repository owner")
    parser.add_argument("repo", help="Repository name")
    parser.add_argument("--startdate", required=True, help="Last UTC calendar day of the window (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, required=True, help="Number of UTC calendar days in the window")
    parser.add_argument("--token", help="GitHub personal access token (or set GITHUB_TOKEN / GITHUB_ENTERPRISE_TOKEN env var)")
    parser.add_argument("--api-url", help="GitHub API base URL for Enterprise (e.g. https://github.corp.example.com/api/v3). Or set GITHUB_API_URL.")
    parser.add_argument("--path", default="page-migrations", help="Directory to look in (default: page-migrations)")
    args = parser.parse_args()

    import os
    api_url = args.api_url or os.environ.get("GITHUB_API_URL")
    token = args.token
    if not token:
        token = os.environ.get("GITHUB_ENTERPRISE_TOKEN") if api_url else None
        token = token or os.environ.get("GITHUB_TOKEN")

    base_url = (api_url or "").rstrip("/") or "https://api.github.com"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    window = resolve_report_window(startdate=args.startdate, days=args.days)

    total = count_pages_migrated(
        base_url, headers, args.owner, args.repo, window.since_day, window.end_day, args.path
    )
    print(total)


if __name__ == "__main__":
    main()
