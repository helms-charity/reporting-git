#!/usr/bin/env python3
"""
Build quarterly-report.html from weekly index.html files under a quarter folder.

python3 generate_quarterly_report.py reports/q2-2026 -o reports/q2-2026/quarterly-report.html

Sums header stats (Total PRs Merged, Pages Migrated) across all weeks and aggregates
per-user metrics from the Individual Reports table in each index (body/div/div[3]/table).
"""

from __future__ import annotations

import argparse
import html
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from index_report_html import (
    STAT_LABELS,
    UserWeekMetrics,
    aggregate_user_metrics,
    collect_index_files,
    parse_header_stat_values,
    parse_individual_reports_table,
)

ROOT = Path(__file__).resolve().parent


def _merge_user_totals(
    quarterly: Dict[str, UserWeekMetrics],
    weekly: Dict[str, UserWeekMetrics],
) -> None:
    for username, metrics in weekly.items():
        if username not in quarterly:
            quarterly[username] = UserWeekMetrics(username=username)
        acc = quarterly[username]
        acc.prs_merged += metrics.prs_merged
        acc.reviews += metrics.reviews
        acc.issues_opened += metrics.issues_opened
        acc.issues_closed += metrics.issues_closed


def write_quarterly_report_html(
    output_path: Path,
    quarter_label: str,
    total_prs_merged: int,
    total_pages_migrated: int,
    week_count: int,
    user_totals: Dict[str, UserWeekMetrics],
    weekly_prs: List[Tuple[str, int]],
    weekly_pages: List[Tuple[str, int]],
) -> None:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sorted_users = sorted(user_totals.values(), key=lambda u: u.username.lower())

    body_rows: List[str] = []
    for user in sorted_users:
        body_rows.append(
            f"""                    <tr>
                        <td class="username-cell">@{html.escape(user.username)}</td>
                        <td class="metric-cell">{user.prs_merged}</td>
                        <td class="metric-cell">{user.reviews}</td>
                        <td class="metric-cell">{user.issues_opened}</td>
                        <td class="metric-cell">{user.issues_closed}</td>
                    </tr>"""
        )
    table_body = "\n".join(body_rows) if body_rows else """                    <tr>
                        <td colspan="5" style="text-align:center;color:#6b7280;">No user rows parsed.</td>
                    </tr>"""

    week_rows_prs = "\n".join(
        f'<li><span class="week">{html.escape(w)}</span> <span class="val">{v}</span></li>'
        for w, v in weekly_prs
    )
    week_rows_pages = "\n".join(
        f'<li><span class="week">{html.escape(w)}</span> <span class="val">{v}</span></li>'
        for w, v in weekly_pages
    )

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quarterly report — {html.escape(quarter_label)}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, oklch(from #667eea 0.7 0.15 260) 0%, oklch(from #764ba2 0.6 0.18 300) 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header, .table-container {{
            background: white;
            border-radius: 16px;
            padding: 32px 40px;
            margin-bottom: 24px;
            box-shadow: 0 10px 40px oklch(from #000 1 0 0 / 0.1);
        }}
        .header h1 {{ font-size: 2.2em; color: oklch(from #1f2937 0.3 0 0); margin-bottom: 8px; }}
        .header p {{ color: oklch(from #6b7280 0.5 0 0); margin-bottom: 16px; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-top: 8px;
        }}
        .stat-card {{
            background: oklch(from #f3f4f6 0.96 0 0);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: oklch(from #667eea 0.6 0.15 260);
        }}
        .stat-label {{ font-size: 0.9em; color: oklch(from #6b7280 0.5 0 0); margin-top: 6px; }}
        .week-breakdown {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-top: 24px;
            font-size: 0.9em;
        }}
        .week-breakdown h3 {{ font-size: 1em; margin-bottom: 8px; color: oklch(from #374151 0.35 0 0); }}
        .week-breakdown ul {{ list-style: none; }}
        .week-breakdown li {{ display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #f3f4f6; }}
        .week-breakdown .val {{ font-family: monospace; font-weight: 600; }}
        h2 {{ font-size: 1.5em; color: oklch(from #1f2937 0.3 0 0); margin-bottom: 16px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{
            text-align: left;
            padding: 14px 12px;
            border-bottom: 2px solid oklch(from #e5e7eb 0.92 0 0);
            color: oklch(from #374151 0.35 0 0);
        }}
        td {{ padding: 12px; border-bottom: 1px solid oklch(from #f3f4f6 0.96 0 0); }}
        tbody tr:hover {{ background: oklch(from #f9fafb 0.98 0 0); }}
        .metric-cell {{ text-align: center; font-family: monospace; }}
        .username-cell {{ font-weight: 600; }}
        .footer {{ text-align: center; color: white; margin-top: 24px; opacity: 0.9; font-size: 0.9em; }}
        @media (max-width: 768px) {{ .week-breakdown {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Quarterly report</h1>
            <p>{html.escape(quarter_label)} · {week_count} weekly index file(s) · Generated {generated}</p>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">{total_prs_merged}</div>
                    <div class="stat-label">{html.escape(STAT_LABELS[0])}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{total_pages_migrated}</div>
                    <div class="stat-label">{html.escape(STAT_LABELS[1])}</div>
                </div>
            </div>
            <div class="week-breakdown">
                <div>
                    <h3>{html.escape(STAT_LABELS[0])} by week</h3>
                    <ul>{week_rows_prs}</ul>
                </div>
                <div>
                    <h3>{html.escape(STAT_LABELS[1])} by week</h3>
                    <ul>{week_rows_pages}</ul>
                </div>
            </div>
        </div>
        <div class="table-container">
            <h2>Summary by User</h2>
            <p style="color: oklch(from #6b7280 0.5 0 0); margin-bottom: 16px;">
                Totals summed from Individual Reports rows across all weekly index pages.
            </p>
            <table>
                <thead>
                    <tr>
                        <th>Username</th>
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
        <div class="footer">reporting-git · generate_quarterly_report.py</div>
    </div>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(doc, encoding="utf-8")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "reports_dir",
        nargs="?",
        default="reports/q2-2026",
        help="Quarter folder with dated */index.html subdirs (default: reports/q2-2026)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output HTML path (default: REPORTS_DIR/quarterly-report.html)",
    )
    args = parser.parse_args(argv)

    reports_dir = Path(args.reports_dir).resolve()
    output_path = (
        args.output.resolve()
        if args.output
        else reports_dir / "quarterly-report.html"
    )
    quarter_label = reports_dir.name

    weekly_prs: List[Tuple[str, int]] = []
    weekly_pages: List[Tuple[str, int]] = []
    user_totals: Dict[str, UserWeekMetrics] = {}
    errors: List[str] = []

    for path in collect_index_files(reports_dir):
        week = path.parent.name
        try:
            content = path.read_text(encoding="utf-8")
            header = parse_header_stat_values(content)
            weekly_prs.append((week, header[0]))
            weekly_pages.append((week, header[1]))
            week_users = parse_individual_reports_table(content)
            _merge_user_totals(user_totals, aggregate_user_metrics(week_users))
        except (OSError, ValueError) as exc:
            errors.append(f"{path}: {exc}")

    if errors:
        for msg in errors:
            print(msg, file=sys.stderr)
        return 1

    total_prs = sum(v for _, v in weekly_prs)
    total_pages = sum(v for _, v in weekly_pages)

    write_quarterly_report_html(
        output_path,
        quarter_label,
        total_prs,
        total_pages,
        len(weekly_prs),
        user_totals,
        weekly_prs,
        weekly_pages,
    )

    print(f"Quarter: {quarter_label}")
    print(f"Weeks:   {len(weekly_prs)}")
    print(f"{STAT_LABELS[0]}: {total_prs}")
    print(f"{STAT_LABELS[1]}: {total_pages}")
    print(f"Users:   {len(user_totals)}")
    print(f"Wrote:   {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
