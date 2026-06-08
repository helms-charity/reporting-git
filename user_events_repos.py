"""
Shared helpers: list owner/repo from GET /users/{login}/events/public,
counting only selected event types (allowlist).

Used by list_repos_from_user_events.py and generate_user_activity_reports.py.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

# GitHub Events API type field (see REST docs). Starring uses WatchEvent, not "StarEvent".
INCLUDED_EVENT_TYPES = frozenset(
    {
        "PullRequestEvent",  # pull request activity (open, close, merge, etc.)
        "IssuesEvent",  # issues (opened, closed, etc.)
    }
)


def parse_iso_utc(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def headers(token: Optional[str]) -> Dict[str, str]:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "reporting-git-user-events-repos",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def resolve_token_and_base(host: str) -> Tuple[str, Optional[str]]:
    """Return (api_base_url, token)."""
    if host == "enterprise":
        base = os.environ.get("GITHUB_API_URL", "").strip().rstrip("/")
        if not base:
            raise ValueError(
                "host=enterprise requires GITHUB_API_URL (e.g. https://github.company.com/api/v3)"
            )
        token = os.environ.get("GITHUB_ENTERPRISE_TOKEN") or os.environ.get("GITHUB_TOKEN")
        return base, token
    if host == "github.com":
        return "https://api.github.com", os.environ.get("GITHUB_TOKEN")
    raise ValueError(f"Unknown host: {host!r} (use 'github.com' or 'enterprise')")


def parse_utc_date(date_str: str) -> datetime:
    """Parse YYYY-MM-DD as UTC midnight."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"Invalid date {date_str!r}; use YYYY-MM-DD") from exc


def report_window_bounds(end_date_str: str, days: int) -> Tuple[datetime, datetime, str, str]:
    """
    N full UTC calendar days ending on end_date_str (last day inclusive).

    Returns (since_dt, end_dt_exclusive, since_day_str, end_day_str) where since_dt is
    00:00 UTC on the first day and end_dt_exclusive is 00:00 UTC on the day after the last.
    """
    if days < 1:
        raise ValueError("days must be >= 1")
    end_day = parse_utc_date(end_date_str)
    since_day = end_day - timedelta(days=days - 1)
    end_exclusive = end_day + timedelta(days=1)
    return (
        since_day,
        end_exclusive,
        since_day.strftime("%Y-%m-%d"),
        end_date_str,
    )


def report_window_bounds_range(
    from_date_str: str, to_date_str: str
) -> Tuple[datetime, datetime, str, str, int]:
    """
    Inclusive UTC calendar range from from_date through to_date (like GitHub profile
    ?from=YYYY-MM-DD&to=YYYY-MM-DD).

    Returns (since_dt, end_exclusive, from_day_str, to_day_str, days).
    """
    from_day = parse_utc_date(from_date_str)
    to_day = parse_utc_date(to_date_str)
    if from_day > to_day:
        raise ValueError(
            f"--from-date {from_date_str} must be on or before --to-date {to_date_str}"
        )
    days = (to_day.date() - from_day.date()).days + 1
    end_exclusive = to_day + timedelta(days=1)
    return from_day, end_exclusive, from_date_str, to_date_str, days


@dataclass(frozen=True)
class ReportWindow:
    """Fixed calendar window or rolling lookback for events + per-repo reports."""

    cutoff: datetime
    end_exclusive: Optional[datetime]
    since_day: str
    end_day: str
    days: int
    report_end_date: Optional[str]
    fixed_calendar: bool


def resolve_report_window(
    *,
    startdate: Optional[str] = None,
    days: int = 7,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> ReportWindow:
    """
    Resolve CLI date options into a single window.

    Use either --from-date + --to-date (inclusive range) or --startdate + --days
    (N UTC days ending on startdate). If only startdate is set, days still applies.
    If none of startdate/from/to are set, uses a rolling window of `days` × 24h ending now.
    """
    has_range = from_date is not None or to_date is not None
    if has_range:
        if not from_date or not to_date:
            raise ValueError("--from-date and --to-date must be used together")
        if startdate:
            raise ValueError(
                "Use either --from-date/--to-date or --startdate/--days, not both"
            )
        since_dt, end_exclusive, since_d, end_d, span_days = report_window_bounds_range(
            from_date, to_date
        )
        return ReportWindow(
            cutoff=since_dt,
            end_exclusive=end_exclusive,
            since_day=since_d,
            end_day=end_d,
            days=span_days,
            report_end_date=to_date,
            fixed_calendar=True,
        )

    if startdate:
        since_dt, end_exclusive, since_d, end_d = report_window_bounds(startdate, days)
        return ReportWindow(
            cutoff=since_dt,
            end_exclusive=end_exclusive,
            since_day=since_d,
            end_day=end_d,
            days=days,
            report_end_date=startdate,
            fixed_calendar=True,
        )

    now = datetime.now(timezone.utc)
    return ReportWindow(
        cutoff=now - timedelta(days=days),
        end_exclusive=None,
        since_day="",
        end_day="",
        days=days,
        report_end_date=None,
        fixed_calendar=False,
    )


def cutoff_for_report_window(end_date_str: str, days: int) -> datetime:
    """UTC midnight at the start of the first inclusive day (matches github_repo_user_report)."""
    since_dt, _, _, _ = report_window_bounds(end_date_str, days)
    return since_dt


def fetch_events_for_user(
    login: str,
    api_base: str,
    token: Optional[str],
    cutoff: datetime,
    end_exclusive: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Paginate GET /users/{login}/events/public until empty or past cutoff.

    When end_exclusive is set (fixed --startdate windows), events at or after that instant
    are skipped; only events in [cutoff, end_exclusive) are kept.
    """
    events: List[Dict[str, Any]] = []
    session = requests.Session()
    hdrs = headers(token)
    for page in range(1, 11):
        url = f"{api_base}/users/{login}/events/public"
        r = session.get(
            url,
            headers=hdrs,
            params={"per_page": 100, "page": page},
            timeout=60,
        )
        if r.status_code == 404:
            return events
        if r.status_code != 200:
            print(
                f"WARN: GET /users/{login}/events/public returned {r.status_code}: "
                f"{(r.text or '')[:200]}",
                file=sys.stderr,
            )
            return events
        batch = r.json()
        if not batch:
            break
        oldest_on_page: Optional[datetime] = None
        for ev in batch:
            created = ev.get("created_at")
            if not created:
                continue
            dt = parse_iso_utc(created)
            if oldest_on_page is None or dt < oldest_on_page:
                oldest_on_page = dt
            if dt < cutoff:
                continue
            if end_exclusive is not None and dt >= end_exclusive:
                continue
            events.append(ev)
        if oldest_on_page is not None and oldest_on_page < cutoff:
            break
        if len(batch) < 100:
            break
    return events


def _repo_full_name_from_event_repo(repo: Dict[str, Any]) -> Optional[str]:
    """
    Events use repo.url (https://api.github.com/repos/owner/name) or name.
    `name` is sometimes only the short repo name; prefer URL so Search/repo APIs match.
    """
    url = (repo.get("url") or "").strip()
    prefix = "/repos/"
    if url and prefix in url:
        tail = url.split(prefix, 1)[1].rstrip("/")
        if tail and "/" in tail:
            return tail
    name = (repo.get("name") or "").strip()
    if not name:
        return None
    if "/" in name:
        return name
    return None


def _repo_from_search_item(item: Dict[str, Any]) -> Optional[str]:
    url = (item.get("repository_url") or "").strip()
    prefix = "/repos/"
    if url and prefix in url:
        tail = url.split(prefix, 1)[1].rstrip("/")
        if tail and "/" in tail:
            return tail
    return None


def collect_repos_from_search(
    login: str,
    api_base: str,
    token: Optional[str],
    since_day: str,
    end_day: str,
    *,
    max_pages_per_query: int = 10,
) -> Tuple[Set[str], Dict[str, int]]:
    """
    Discover owner/repo via Search API for a UTC calendar range.

    Uses the same qualifiers as github_repo_user_report (author, commenter,
    reviewed-by). Unlike GET /users/{login}/events/public (~300 events, ~90 days),
    search can reach further back when --from-date/--to-date span weeks or months.
    """
    date_range = f"{since_day}..{end_day}"
    queries: List[Tuple[str, str]] = [
        ("author", f"author:{login} created:{date_range}"),
        ("commenter", f"commenter:{login} created:{date_range}"),
        ("reviewed-by", f"reviewed-by:{login} created:{date_range}"),
    ]
    repos: Set[str] = set()
    hit_counts: Dict[str, int] = {}
    session = requests.Session()
    hdrs = headers(token)

    for label, query in queries:
        found = 0
        for page in range(1, max_pages_per_query + 1):
            r = session.get(
                f"{api_base}/search/issues",
                headers=hdrs,
                params={"q": query, "per_page": 100, "page": page},
                timeout=60,
            )
            if r.status_code != 200:
                print(
                    f"WARN: search/issues ({label}) returned {r.status_code}: "
                    f"{(r.text or '')[:200]}",
                    file=sys.stderr,
                )
                break
            data = r.json()
            items = data.get("items") or []
            for item in items:
                full = _repo_from_search_item(item)
                if full:
                    repos.add(full)
            found += len(items)
            total = data.get("total_count", 0)
            if page * 100 >= total or len(items) < 100:
                break
        hit_counts[label] = found

    return repos, hit_counts


def collect_repos_from_events(events: List[Dict[str, Any]]) -> Tuple[Set[str], Dict[str, int]]:
    """
    Return (repo full names owner/repo, per-type counts) for INCLUDED_EVENT_TYPES only.

    IssuesEvent: only opened / closed / reopened are counted toward discovery, so a repo
    is not added for label-only, assign-only, etc. (those do not appear on github_repo_user_report
    issue metric cards).
    """
    repos: Set[str] = set()
    type_counts: Dict[str, int] = {}
    for ev in events:
        et = ev.get("type") or ""
        if et not in INCLUDED_EVENT_TYPES:
            continue
        if et == "IssuesEvent":
            payload = ev.get("payload") or {}
            act = (payload.get("action") or "").lower()
            if act and act not in ("opened", "closed", "reopened"):
                continue
        type_counts[et] = type_counts.get(et, 0) + 1
        repo = ev.get("repo") or {}
        full = _repo_full_name_from_event_repo(repo)
        if full:
            repos.add(full)
    return repos, type_counts
