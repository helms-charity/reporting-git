"""
Shared helpers: list owner/repo from GET /users/{login}/events/public,
counting only selected event types (allowlist).

Used by list_repos_from_user_events.py and generate_user_activity_reports.py.
"""

from __future__ import annotations

import os
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


def cutoff_for_report_window(end_date_str: str, days: int) -> datetime:
    """
    Match github_repo_user_report window: since_date = end_date - days (naive UTC midnight end date).
    """
    end = datetime.strptime(end_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return end - timedelta(days=days)


def fetch_events_for_user(
    login: str,
    api_base: str,
    token: Optional[str],
    cutoff: datetime,
) -> List[Dict[str, Any]]:
    """Paginate GET /users/{login}/events/public until empty or past cutoff."""
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
            return events
        batch = r.json()
        if not batch:
            break
        for ev in batch:
            created = ev.get("created_at")
            if not created:
                continue
            dt = parse_iso_utc(created)
            if dt < cutoff:
                return events
            events.append(ev)
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
