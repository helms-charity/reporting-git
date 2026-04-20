#!/usr/bin/env python3
"""
Multi-repo user activity orchestration (JSON ledger + HTML reports).

Repo discovery: use --repos-from-events (public events, same as list_repos_from_user_events.py),
or GET /user/repos plus optional --repos-config allowlist (intersect by default).

Writes reports/user_activity/ JSON ledgers, reports/team/ HTML (skipped when a repo has no
measurable activity in the window), runs generate_team_index.py.
See user_activity_ledger.example.json and repos_allowlist.example.json.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

from user_events_repos import (
    collect_repos_from_events,
    cutoff_for_report_window,
    fetch_events_for_user,
)

ROOT = Path(__file__).resolve().parent
SCHEMA_VERSION = 1


def _sanitize_filename_segment(s: str) -> str:
    """Safe single path segment (no slashes)."""
    return re.sub(r"[^\w.\-]+", "_", s)


def load_user_names(path: Path) -> List[Tuple[str, str]]:
    """Return list of (login, host) for every account in user_names.json."""
    data = json.loads(path.read_text(encoding="utf-8"))
    out: List[Tuple[str, str]] = []
    for person in data.get("people", []):
        for acc in person.get("accounts", []):
            login = acc.get("login")
            host = acc.get("host", "github.com")
            if login:
                out.append((login, host))
    return out


def load_tokens_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def api_base_for_host(host: str) -> str:
    if host == "enterprise":
        base = os.environ.get("GITHUB_API_URL", "").strip().rstrip("/")
        if not base:
            raise ValueError("host=enterprise requires GITHUB_API_URL")
        return base
    return "https://api.github.com"


def resolve_token_for_account(
    login: str,
    host: str,
    tokens_map: Dict[str, str],
) -> Optional[str]:
    if login in tokens_map:
        return tokens_map[login]
    if host == "enterprise":
        return os.environ.get("GITHUB_ENTERPRISE_TOKEN") or os.environ.get("GITHUB_TOKEN")
    return os.environ.get("GITHUB_TOKEN")


def github_headers(token: Optional[str]) -> Dict[str, str]:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "reporting-git-generate-user-activity",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def get_rate_limit_remaining(token: Optional[str], api_base: str) -> Optional[int]:
    try:
        r = requests.get(
            f"{api_base}/rate_limit",
            headers=github_headers(token),
            timeout=30,
        )
        if r.status_code != 200:
            return None
        core = r.json().get("resources", {}).get("core", {})
        return int(core.get("remaining", 0))
    except Exception:
        return None


def fetch_user_repos_from_api(
    token: Optional[str],
    api_base: str,
    exclude_forks: bool,
    exclude_archived: bool,
    org_filters: Optional[List[str]],
) -> Set[str]:
    """Paginate GET /user/repos; return set of owner/repo strings."""
    if not token:
        return set()
    repos: Set[str] = set()
    url = f"{api_base}/user/repos"
    params = {
        "per_page": 100,
        "affiliation": "owner,collaborator,organization_member",
        "sort": "full_name",
    }
    session = requests.Session()
    page = 1
    while True:
        r = session.get(
            url,
            headers=github_headers(token),
            params={**params, "page": page},
            timeout=60,
        )
        if r.status_code != 200:
            raise RuntimeError(f"GET /user/repos failed: {r.status_code} {r.text[:400]}")
        batch = r.json()
        if not batch:
            break
        for repo in batch:
            if exclude_forks and repo.get("fork"):
                continue
            if exclude_archived and repo.get("archived"):
                continue
            full = repo.get("full_name")
            if not full:
                continue
            if org_filters:
                owner = (repo.get("owner") or {}).get("login", "")
                if owner not in org_filters:
                    continue
            repos.add(full)
        if len(batch) < 100:
            break
        page += 1
    return repos


def fetch_org_repos(
    token: Optional[str],
    api_base: str,
    org: str,
    exclude_forks: bool,
    exclude_archived: bool,
) -> Set[str]:
    if not token:
        return set()
    repos: Set[str] = set()
    session = requests.Session()
    page = 1
    while True:
        r = session.get(
            f"{api_base}/orgs/{org}/repos",
            headers=github_headers(token),
            params={"per_page": 100, "page": page, "type": "all"},
            timeout=60,
        )
        if r.status_code == 404:
            # try users/{org}/repos for user-owned namespace
            r = session.get(
                f"{api_base}/users/{org}/repos",
                headers=github_headers(token),
                params={"per_page": 100, "page": page, "type": "all"},
                timeout=60,
            )
        if r.status_code != 200:
            raise RuntimeError(f"Listing org/user {org} repos failed: {r.status_code} {r.text[:400]}")
        batch = r.json()
        if not batch:
            break
        for repo in batch:
            if exclude_forks and repo.get("fork"):
                continue
            if exclude_archived and repo.get("archived"):
                continue
            full = repo.get("full_name")
            if full:
                repos.add(full)
        if len(batch) < 100:
            break
        page += 1
    return repos


def load_repos_allowlist(path: Path) -> Tuple[List[str], List[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    repos = list(data.get("repos") or [])
    orgs = list(data.get("orgs") or [])
    return repos, orgs


def expand_allowlist(
    path: Path,
    token: Optional[str],
    api_base: str,
    exclude_forks: bool,
    exclude_archived: bool,
) -> Set[str]:
    explicit, orgs = load_repos_allowlist(path)
    out: Set[str] = set()
    for r in explicit:
        r = r.strip()
        if r and "/" in r:
            out.add(r)
    for org in orgs:
        org = org.strip()
        if not org:
            continue
        if not token:
            raise RuntimeError(f"Listing org {org} requires a token")
        out |= fetch_org_repos(token, api_base, org, exclude_forks, exclude_archived)
    return out


def intersect_repos(api_repos: Set[str], allow_repos: Set[str]) -> Set[str]:
    """Case-insensitive intersection; keep casing from api_repos when possible."""
    allow_l = {x.lower() for x in allow_repos}
    return {x for x in api_repos if x.lower() in allow_l}


def union_repos(api_repos: Set[str], allow_repos: Set[str]) -> Set[str]:
    """Union with dedupe by lower case; prefer names from api_repos."""
    by_l = {x.lower(): x for x in api_repos}
    for x in allow_repos:
        xl = x.lower()
        if xl not in by_l:
            by_l[xl] = x
    return set(by_l.values())


def verify_token_user(login: str, token: Optional[str], api_base: str) -> bool:
    """Optional: ensure /user login matches expected account."""
    if not token:
        return False
    try:
        r = requests.get(
            f"{api_base}/user",
            headers=github_headers(token),
            timeout=30,
        )
        if r.status_code != 200:
            return False
        return (r.json().get("login") or "").lower() == login.lower()
    except Exception:
        return False


def write_ledger(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def run_report_subprocess(
    owner: str,
    repo: str,
    username: str,
    days: int,
    report_end_date: Optional[str],
    out_html: Path,
    token: Optional[str],
    api_url: Optional[str],
) -> Tuple[int, str, str]:
    """
    Run github_repo_user_report.py. If report_end_date is None, do not pass --startdate
    (end of window is current time in UTC inside github_repo_user_report.analyze_activity).
    """
    cmd = [
        sys.executable,
        str(ROOT / "github_repo_user_report.py"),
        owner,
        repo,
        username,
        "--days",
        str(days),
        "--format",
        "html",
        "--pages-migrated",
        "0",
        "--output",
        str(out_html),
    ]
    if report_end_date:
        cmd.extend(["--startdate", report_end_date])
    cmd.append("--omit-if-empty")
    if token:
        cmd.extend(["--token", token])
    if api_url:
        cmd.extend(["--api-url", api_url])
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=600,
    )
    err = (proc.stderr or "") + ("\n" + proc.stdout if proc.returncode != 0 else "")
    stderr_tail = (proc.stderr or "")[-4000:]
    return proc.returncode, err[-2000:] if err else "", stderr_tail


def parse_accounts_arg(users_csv: Optional[str]) -> Optional[Set[str]]:
    if not users_csv:
        return None
    return {x.strip() for x in users_csv.split(",") if x.strip()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-user-names",
        action="store_true",
        help="Load all accounts from user_names.json",
    )
    parser.add_argument(
        "--user-names",
        type=Path,
        default=ROOT / "user_names.json",
        help="Path to user_names.json",
    )
    parser.add_argument(
        "--users",
        help="Comma-separated logins to include (subset when using --from-user-names)",
    )
    parser.add_argument(
        "--repos-config",
        type=Path,
        help="repos_allowlist JSON (repos + optional orgs); ignored if --repos-from-events",
    )
    parser.add_argument(
        "--repos-from-events",
        action="store_true",
        help="Discover repos from public events only (no GET /user/repos, no allowlist). "
        "Matches list_repos_from_user_events.py (PullRequestEvent and IssuesEvent only).",
    )
    parser.add_argument(
        "--tokens-file",
        type=Path,
        help="JSON map login -> PAT (optional; else env tokens)",
    )
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument(
        "--startdate",
        type=str,
        default=None,
        help="End date YYYY-MM-DD for the repo report window. If omitted, matches weekly scripts: "
        "github_repo_user_report uses now UTC as the window end (do not pass --startdate). "
        "Ledger filenames still use today UTC when this is omitted.",
    )
    parser.add_argument(
        "--org",
        action="append",
        dest="orgs",
        help="Only include repos whose owner login matches (repeatable); applies to API list",
    )
    parser.add_argument("--include-forks", action="store_true", help="Include forked repos")
    parser.add_argument(
        "--include-archived",
        action="store_true",
        help="Include archived repos",
    )
    parser.add_argument(
        "--union-allowlist",
        action="store_true",
        help="If both API and allowlist: union instead of intersection",
    )
    parser.add_argument(
        "--skip-user-verify",
        action="store_true",
        help="Do not warn when PAT /user login differs from target login",
    )
    parser.add_argument("--sleep-seconds", type=float, default=2.0, help="Delay between repo reports")
    parser.add_argument(
        "--rate-limit-min",
        type=int,
        default=80,
        help="If remaining core requests below this, sleep 60s before continuing",
    )
    parser.add_argument("--max-repos", type=int, default=0, help="Cap repos per user (0 = no cap)")
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="Skip generate_team_index.py at the end",
    )
    args = parser.parse_args()

    ledger_date = args.startdate or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_end_date = args.startdate
    date_compact = ledger_date.replace("-", "")
    exclude_forks = not args.include_forks
    exclude_archived = not args.include_archived
    tokens_map = load_tokens_file(args.tokens_file) if args.tokens_file else {}

    if not args.from_user_names:
        parser.error("Currently require --from-user-names (or extend with explicit --user/--host pairs later)")

    accounts = load_user_names(args.user_names)
    filt = parse_accounts_arg(args.users)
    if filt:
        accounts = [(l, h) for l, h in accounts if l in filt]

    if not accounts:
        print("No accounts to process.", file=sys.stderr)
        sys.exit(1)

    team_dir = ROOT / "reports" / "team"
    ledger_dir = ROOT / "reports" / "user_activity"
    team_dir.mkdir(parents=True, exist_ok=True)

    for login, host in accounts:
        print(f"\n=== Account @{login} ({host}) ===")
        try:
            api_base = api_base_for_host(host)
        except ValueError as e:
            print(f"SKIP: {e}", file=sys.stderr)
            continue

        token = resolve_token_for_account(login, host, tokens_map)
        api_url = api_base if host == "enterprise" else None

        final_set: Set[str]
        token_source: str
        api_set: Set[str] = set()
        allow_set: Set[str] = set()

        if args.repos_from_events:
            if args.repos_config and args.repos_config.exists():
                print(
                    "WARN: --repos-config is ignored when using --repos-from-events",
                    file=sys.stderr,
                )
            if host == "enterprise" and not token:
                print(
                    "SKIP: enterprise requires GITHUB_ENTERPRISE_TOKEN or GITHUB_TOKEN for events API",
                    file=sys.stderr,
                )
                continue
            if not token and host == "github.com":
                print(
                    f"  [{login}] WARNING: GITHUB_TOKEN not set — public events limited to 60 req/hr",
                    file=sys.stderr,
                )
            if args.startdate:
                cutoff = cutoff_for_report_window(args.startdate, args.days)
            else:
                cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
            events = fetch_events_for_user(login, api_base, token, cutoff)
            final_set, _ = collect_repos_from_events(events)
            token_source = "public_events"
        else:
            has_allowlist = args.repos_config and args.repos_config.exists()
            if has_allowlist:
                allow_set = expand_allowlist(
                    args.repos_config,
                    token,
                    api_base,
                    exclude_forks,
                    exclude_archived,
                )

            if token:
                try:
                    api_set = fetch_user_repos_from_api(
                        token,
                        api_base,
                        exclude_forks,
                        exclude_archived,
                        args.orgs,
                    )
                except RuntimeError as e:
                    print(f"WARN: API repo list failed: {e}", file=sys.stderr)

            if not token and not has_allowlist:
                print("SKIP: No token and no allowlist — cannot resolve repos.", file=sys.stderr)
                continue

            if token and not args.skip_user_verify:
                if not verify_token_user(login, token, api_base):
                    print(
                        f"WARN: Token does not match login @{login} (/user). "
                        f"Use per-login entry in --tokens-file or --skip-user-verify.",
                        file=sys.stderr,
                    )

            has_allowlist_bool = bool(allow_set)
            has_api_data = bool(token)

            if has_api_data and has_allowlist_bool:
                if not api_set:
                    final_set = set(allow_set)
                    token_source = "allowlist"
                elif args.union_allowlist:
                    final_set = union_repos(api_set, allow_set)
                    token_source = "pat_and_allowlist_union"
                else:
                    final_set = intersect_repos(api_set, allow_set)
                    token_source = "pat_and_allowlist"
                    if not final_set and allow_set:
                        print(
                            "WARN: intersection empty; using allowlist-only for this user.",
                            file=sys.stderr,
                        )
                        final_set = set(allow_set)
                        token_source = "allowlist"
            elif has_api_data:
                final_set = set(api_set)
                token_source = "pat"
            elif has_allowlist_bool:
                final_set = set(allow_set)
                token_source = "allowlist"
            else:
                print("SKIP: Could not resolve repository list.", file=sys.stderr)
                continue

        if not final_set:
            print("WARN: No repositories to report — skipping user.", file=sys.stderr)
            continue

        final_list = sorted(final_set, key=str.lower)
        if args.max_repos > 0:
            final_list = final_list[: args.max_repos]

        repos_considered: List[Dict[str, str]] = []
        if args.repos_from_events:
            for fn in final_list:
                repos_considered.append({"full_name": fn, "source": "public_events"})
        else:
            api_set_lower = {x.lower() for x in api_set}
            allow_set_lower = {x.lower() for x in allow_set}
            for fn in final_list:
                fl = fn.lower()
                if fl in api_set_lower and fl in allow_set_lower:
                    src = "intersection" if not args.union_allowlist else "mixed"
                elif fl in api_set_lower:
                    src = "api"
                else:
                    src = "allowlist"
                repos_considered.append({"full_name": fn, "source": src})

        # Simplify source tagging: mark as mixed
        ledger: Dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "date": ledger_date,
            "username": login,
            "host": host,
            "token_source": token_source,
            "days": args.days,
            "repos_considered": repos_considered,
            "runs": [],
            "summary": {"ok": 0, "error": 0, "skipped": 0},
        }

        ledger_path = ledger_dir / f"{login}-{date_compact}.json"

        for item in final_list:
            parts = item.split("/", 1)
            if len(parts) != 2:
                ledger["summary"]["skipped"] += 1
                ledger["runs"].append(
                    {"full_name": item, "status": "skipped", "error": "invalid full_name"}
                )
                write_ledger(ledger_path, ledger)
                continue
            owner, repo_name = parts[0], parts[1]
            owner_seg = _sanitize_filename_segment(owner)
            repo_seg = _sanitize_filename_segment(repo_name)
            out_name = f"{login}-{owner_seg}-{repo_seg}-{ledger_date}.html"
            out_html = team_dir / out_name

            rem = get_rate_limit_remaining(token, api_base)
            if rem is not None and rem < args.rate_limit_min:
                print(f"Rate limit low ({rem}); sleeping 60s...")
                time.sleep(60)

            code, err, stderr_tail = run_report_subprocess(
                owner,
                repo_name,
                login,
                args.days,
                report_end_date,
                out_html,
                token,
                api_url,
            )
            rem_after = get_rate_limit_remaining(token, api_base)
            rel_path = str(out_html.relative_to(ROOT))
            if code == 0:
                ledger["summary"]["ok"] += 1
                run_entry: Dict[str, Any] = {
                    "full_name": item,
                    "status": "ok",
                    "html_path": rel_path,
                    "rate_limit_remaining": rem_after,
                }
                if stderr_tail.strip():
                    run_entry["report_stderr_tail"] = stderr_tail.strip()
                ledger["runs"].append(run_entry)
                print(f"  {item} -> ok ({rel_path})")
            elif code == 2:
                ledger["summary"]["skipped"] += 1
                if out_html.exists():
                    out_html.unlink()
                ledger["runs"].append(
                    {
                        "full_name": item,
                        "status": "empty",
                        "reason": "no merged PRs, reviews, or issue activity in window",
                        "rate_limit_remaining": rem_after,
                        "report_stderr_tail": stderr_tail.strip() if stderr_tail.strip() else None,
                    }
                )
                print(f"  {item} -> skipped (empty window, no HTML)")
            else:
                ledger["summary"]["error"] += 1
                ledger["runs"].append(
                    {
                        "full_name": item,
                        "status": "error",
                        "error": err[:500],
                        "rate_limit_remaining": rem_after,
                        "report_stderr_tail": stderr_tail.strip() if stderr_tail.strip() else None,
                    }
                )
                print(f"  {item} -> error {code} ({rel_path})")
            write_ledger(ledger_path, ledger)
            time.sleep(args.sleep_seconds)

        print(f"Ledger: {ledger_path}")

    if not args.no_index:
        print("\nRunning generate_team_index.py ...")
        subprocess.run([sys.executable, str(ROOT / "generate_team_index.py")], cwd=str(ROOT), check=False)


if __name__ == "__main__":
    main()
