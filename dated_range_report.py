"""
Consolidated HTML table for --from-date / --to-date activity runs.
Repo discovery uses the public events feed (see generate_user_activity_reports.py).
"""

from __future__ import annotations

import contextlib
import html
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from github_repo_user_report import GitHubRepoUserAnalyzer
from user_events_repos import ReportWindow


def collect_repo_activity_counts(
    owner: str,
    repo: str,
    username: str,
    window: ReportWindow,
    token: Optional[str],
    api_url: Optional[str],
) -> Dict[str, int]:
    """Run github_repo_user_report analysis and return summary counts."""
    analyzer = GitHubRepoUserAnalyzer(owner, repo, username, token, base_url=api_url)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        analyzer.analyze_activity(
            window.days,
            window.end_exclusive,
            window.cutoff,
        )
    return {
        "prs_merged": len(analyzer.stats["pull_requests_merged"]),
        "reviews": analyzer.stats.get(
            "total_reviews_given", len(analyzer.stats["pull_requests_reviewed"])
        ),
        "issues_opened": len(analyzer.stats["issues_opened"]),
        "issues_closed": len(analyzer.stats["issues_closed"]),
    }


def dated_report_output_path(reports_dir: Path, from_date: str, to_date: str) -> Path:
    return reports_dir / f"dated-report-{from_date}-to-{to_date}.html"


def write_dated_report_html(
    output_path: Path,
    rows: List[Dict[str, Any]],
    from_date: str,
    to_date: str,
) -> None:
    """Write a single HTML page with Username / Repository / metric columns."""
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_prs = sum(int(r.get("prs_merged", 0)) for r in rows)
    total_reviews = sum(int(r.get("reviews", 0)) for r in rows)
    total_opened = sum(int(r.get("issues_opened", 0)) for r in rows)
    total_closed = sum(int(r.get("issues_closed", 0)) for r in rows)

    body_rows: List[str] = []
    for row in sorted(rows, key=lambda r: (r["username"].lower(), r["repository"].lower())):
        username = html.escape(row["username"])
        repository = html.escape(row["repository"])
        prs = int(row.get("prs_merged", 0))
        reviews = int(row.get("reviews", 0))
        opened = int(row.get("issues_opened", 0))
        closed = int(row.get("issues_closed", 0))

        def cell(value: int) -> str:
            cls = ' class="metric-cell positive"' if value else ' class="metric-cell"'
            return f"<td{cls}>{value}</td>"

        body_rows.append(
            f"""                    <tr>
                        <td class="username-cell">@{username}</td>
                        <td class="repo-cell">{repository}</td>
                        {cell(prs)}
                        {cell(reviews)}
                        {cell(opened)}
                        {cell(closed)}
                    </tr>"""
        )

    table_body = "\n".join(body_rows) if body_rows else """                    <tr>
                        <td colspan="6" style="text-align:center;color:#6b7280;">No repositories discovered for this window.</td>
                    </tr>"""

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Activity report {html.escape(from_date)} – {html.escape(to_date)}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, oklch(from #667eea 0.7 0.15 260) 0%, oklch(from #764ba2 0.6 0.18 300) 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            border-radius: 16px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px oklch(from #000000 1 0 0 / 0.1);
        }}
        .header h1 {{
            font-size: 2.2em;
            color: oklch(from #1f2937 0.3 0 0);
            margin-bottom: 10px;
        }}
        .header p {{
            font-size: 1.05em;
            color: oklch(from #6b7280 0.5 0 0);
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 16px;
            margin-top: 20px;
        }}
        .stat-card {{
            background: oklch(from #f3f4f6 0.96 0 0);
            padding: 16px;
            border-radius: 12px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 1.8em;
            font-weight: bold;
            color: oklch(from #667eea 0.6 0.15 260);
        }}
        .stat-label {{
            font-size: 0.85em;
            color: oklch(from #6b7280 0.5 0 0);
            margin-top: 4px;
        }}
        .table-container {{
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 10px 40px oklch(from #000000 1 0 0 / 0.1);
            overflow-x: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95em;
        }}
        thead {{
            background: oklch(from #f9fafb 0.98 0 0);
        }}
        th {{
            padding: 16px 12px;
            text-align: left;
            font-weight: 600;
            color: oklch(from #374151 0.35 0 0);
            border-bottom: 2px solid oklch(from #e5e7eb 0.92 0 0);
            white-space: nowrap;
        }}
        td {{
            padding: 14px 12px;
            border-bottom: 1px solid oklch(from #f3f4f6 0.96 0 0);
            color: oklch(from #1f2937 0.3 0 0);
        }}
        tbody tr:hover {{
            background: oklch(from #f9fafb 0.98 0 0);
        }}
        .metric-cell {{
            text-align: center;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
        }}
        .username-cell {{
            font-weight: 600;
        }}
        .repo-cell {{
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
            font-size: 0.9em;
        }}
        .positive {{
            color: oklch(from #10b981 0.55 0.15 150);
        }}
        .footer {{
            text-align: center;
            color: white;
            margin-top: 30px;
            opacity: 0.9;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Activity report</h1>
            <p>UTC calendar window: <strong>{html.escape(from_date)}</strong> through <strong>{html.escape(to_date)}</strong> (inclusive)</p>
            <p>Generated: {generated} · {len(rows)} row(s)</p>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">{total_prs}</div>
                    <div class="stat-label">PRs Merged</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{total_reviews}</div>
                    <div class="stat-label">Reviews</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{total_opened}</div>
                    <div class="stat-label">Issues Opened</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{total_closed}</div>
                    <div class="stat-label">Issues Closed</div>
                </div>
            </div>
        </div>
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Username</th>
                        <th>Repository</th>
                        <th>PRs Merged</th>
                        <th>Reviews</th>
                        <th>Issues Opened</th>
                        <th>Issues Closed</th>
                    </tr>
                </thead>
                <tbody>
{table_body}
                </tbody>
            </table>
        </div>
        <div class="footer">
            reporting-git · dated range report
        </div>
    </div>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(doc, encoding="utf-8")
