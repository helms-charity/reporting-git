"""
Parse weekly team index.html files produced by generate_team_index.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

STAT_VALUE_RE = re.compile(
    r'<div class="stat-value">([^<]*)</div>',
    re.IGNORECASE,
)
STATS_BLOCK_RE = re.compile(
    r'<div class="stats">(.*?)</div>\s*</div>\s*<div class="table-container">',
    re.DOTALL | re.IGNORECASE,
)
INDIVIDUAL_REPORTS_BLOCK_RE = re.compile(
    r"Individual Reports.*?<table>(.*?)</table>",
    re.DOTALL | re.IGNORECASE,
)
TABLE_ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
TABLE_CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL | re.IGNORECASE)

STAT_LABELS = ("Total PRs Merged", "Pages Migrated", "Repositories")

USER_METRIC_COLUMNS = (
    "prs_merged",
    "reviews",
    "issues_opened",
    "issues_closed",
)


@dataclass
class UserWeekMetrics:
    username: str
    prs_merged: int = 0
    reviews: int = 0
    issues_opened: int = 0
    issues_closed: int = 0


def collect_index_files(reports_dir: Path) -> List[Path]:
    if not reports_dir.is_dir():
        raise FileNotFoundError(f"reports directory not found: {reports_dir}")
    files = sorted(reports_dir.glob("*/index.html"))
    if not files:
        raise FileNotFoundError(f"no */index.html under {reports_dir}")
    return files


def parse_header_stat_values(html: str) -> List[int]:
    match = STATS_BLOCK_RE.search(html)
    if not match:
        raise ValueError("header stats block not found")
    raw_values = STAT_VALUE_RE.findall(match.group(1))
    if not raw_values:
        raise ValueError("no stat-value elements in header stats")
    values: List[int] = []
    for raw in raw_values:
        text = raw.strip().replace(",", "")
        if not text.isdigit():
            raise ValueError(f"non-integer stat value: {raw!r}")
        values.append(int(text))
    return values


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_metric_int(text: str) -> int:
    cleaned = re.sub(r"[^\d]", "", text.strip())
    return int(cleaned) if cleaned else 0


def _normalize_username(cell_html: str) -> str:
    text = _strip_html(cell_html)
    return text.lstrip("@").strip()


def parse_individual_reports_table(html: str) -> List[UserWeekMetrics]:
    """
    Parse the Individual Reports table (container div[3] under .container).

    Columns: Date, Username, Repository, PRs Merged, Reviews, Issues Opened,
    Issues Closed, ...
    """
    block = INDIVIDUAL_REPORTS_BLOCK_RE.search(html)
    if not block:
        raise ValueError("Individual Reports table not found")

    rows: List[UserWeekMetrics] = []
    for row_html in TABLE_ROW_RE.findall(block.group(1)):
        if "<th" in row_html.lower():
            continue
        cells = [_strip_html(c) for c in TABLE_CELL_RE.findall(row_html)]
        if len(cells) < 7:
            continue
        username = _normalize_username(cells[1])
        if not username:
            continue
        rows.append(
            UserWeekMetrics(
                username=username,
                prs_merged=_parse_metric_int(cells[3]),
                reviews=_parse_metric_int(cells[4]),
                issues_opened=_parse_metric_int(cells[5]),
                issues_closed=_parse_metric_int(cells[6]),
            )
        )
    return rows


def aggregate_user_metrics(rows: List[UserWeekMetrics]) -> Dict[str, UserWeekMetrics]:
    totals: Dict[str, UserWeekMetrics] = {}
    for row in rows:
        if row.username not in totals:
            totals[row.username] = UserWeekMetrics(username=row.username)
        acc = totals[row.username]
        acc.prs_merged += row.prs_merged
        acc.reviews += row.reviews
        acc.issues_opened += row.issues_opened
        acc.issues_closed += row.issues_closed
    return totals
