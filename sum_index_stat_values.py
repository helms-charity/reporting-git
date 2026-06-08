#!/usr/bin/env python3
"""
Sum a header stat from weekly team index.html reports.

Each index page has three values under div.header > div.stats (Total PRs Merged,
Pages Migrated, Repositories). By default this script reads the second stat-card
(stat-index 1), which matches XPath:

  /html/body/div/div[1]/div/div[2]/div[1]

Use --stat-index to sum a different card (0 = PRs, 1 = pages, 2 = repos).

For a full quarterly HTML report, use generate_quarterly_report.py.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from index_report_html import STAT_LABELS, collect_index_files, parse_header_stat_values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sum a header stat-value from weekly index.html reports.",
    )
    parser.add_argument(
        "reports_dir",
        nargs="?",
        default="reports/q2-2026",
        help="Quarter/week folder containing dated subdirs (default: reports/q2-2026)",
    )
    parser.add_argument(
        "--stat-index",
        type=int,
        default=1,
        choices=(0, 1, 2),
        metavar="N",
        help="0-based index of stat-card in header (default: 1, Pages Migrated; "
        "matches XPath /html/body/div/div[1]/div/div[2]/div[1])",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only the total sum",
    )
    args = parser.parse_args(argv)

    reports_dir = Path(args.reports_dir).resolve()
    stat_index = args.stat_index

    rows: list[tuple[str, int]] = []
    errors: list[str] = []

    for path in collect_index_files(reports_dir):
        week = path.parent.name
        try:
            html = path.read_text(encoding="utf-8")
            values = parse_header_stat_values(html)
            if stat_index >= len(values):
                raise ValueError(
                    f"stat-index {stat_index} out of range (found {len(values)} stats)"
                )
            rows.append((week, values[stat_index]))
        except (OSError, ValueError) as exc:
            errors.append(f"{path}: {exc}")

    if errors:
        for msg in errors:
            print(msg, file=sys.stderr)
        return 1

    total = sum(value for _, value in rows)
    label = STAT_LABELS[stat_index] if stat_index < len(STAT_LABELS) else f"stat {stat_index}"

    if not args.quiet:
        print(f"Reports: {reports_dir}")
        print(f"Metric:  {label} (stat-index {stat_index})")
        print(f"Files:   {len(rows)}")
        print()
        for week, value in rows:
            print(f"  {week}: {value}")
        print()
        print(f"Total: {total}")
    else:
        print(total)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
