#!/usr/bin/env python3
"""
Generate Team Index Page

Scans reports/team/ directory for HTML reports and creates an index.html
with a table showing all metrics from each report.
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from html.parser import HTMLParser
from typing import Dict, List, Optional


class ReportMetricsParser(HTMLParser):
    """Parse HTML report to extract metrics"""
    
    def __init__(self):
        super().__init__()
        self.in_repo_div = False
        self.in_username_div = False
        self.in_metric_card = False
        self.in_metric_label = False
        self.in_metric_value = False
        self.current_label = None
        self.metrics = {}
        self.username = None
        self.repo_owner = None
        self.repo_name = None
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        # Check for repo div
        if tag == 'div' and attrs_dict.get('class') == 'repo':
            self.in_repo_div = True
        
        # Check for username div
        if tag == 'div' and attrs_dict.get('class') == 'username':
            self.in_username_div = True
        
        # Check for metric cards
        if tag == 'div' and attrs_dict.get('class') == 'metric-card':
            self.in_metric_card = True
        
        if self.in_metric_card:
            if tag == 'div' and attrs_dict.get('class') == 'metric-label':
                self.in_metric_label = True
            elif tag == 'div' and attrs_dict.get('class') == 'metric-value':
                self.in_metric_value = True
    
    def handle_endtag(self, tag):
        if tag == 'div':
            if self.in_repo_div:
                self.in_repo_div = False
            elif self.in_username_div:
                self.in_username_div = False
            elif self.in_metric_label:
                self.in_metric_label = False
            elif self.in_metric_value:
                self.in_metric_value = False
            elif self.in_metric_card:
                self.in_metric_card = False
                self.current_label = None
    
    def handle_data(self, data):
        data = data.strip()
        if not data:
            return
        
        # Extract repo (format: "owner/repo")
        if self.in_repo_div:
            parts = data.split('/')
            if len(parts) == 2:
                self.repo_owner = parts[0]
                self.repo_name = parts[1]
        
        # Extract username (format: "@username")
        if self.in_username_div:
            self.username = data.lstrip('@')
        
        # Extract metric label and value
        if self.in_metric_label:
            self.current_label = data
        elif self.in_metric_value and self.current_label:
            self.metrics[self.current_label] = data


def parse_report_file(filepath: Path) -> Optional[Dict]:
    """Parse a single report HTML file and extract metrics"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        parser = ReportMetricsParser()
        parser.feed(content)
        
        if not parser.username or not parser.repo_owner:
            return None
        
        # Extract date from filename or use file modification time
        # Expected format: username-repo_name-yyyy-mm-dd.html
        filename = filepath.stem
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        if date_match:
            report_date = date_match.group(1)
        else:
            # Use file modification time
            mtime = filepath.stat().st_mtime
            report_date = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
        
        return {
            'filename': filepath.name,
            'date': report_date,
            'username': parser.username,
            'repo': f"{parser.repo_owner}/{parser.repo_name}",
            'metrics': parser.metrics
        }
    
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None


def generate_index_html(reports: List[Dict], output_path: Path):
    """Generate index.html with table of all reports"""
    
    # Sort reports by date (newest first), then by username
    reports.sort(key=lambda x: (x['date'], x['username']), reverse=True)
    
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Team Activity Reports Index</title>
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
            font-size: 2.5em;
            color: oklch(from #1f2937 0.3 0 0);
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 1.1em;
            color: oklch(from #6b7280 0.5 0 0);
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
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
        
        .stat-label {{
            font-size: 0.9em;
            color: oklch(from #6b7280 0.5 0 0);
            margin-top: 5px;
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
            position: sticky;
            top: 0;
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
        
        tbody tr {{
            transition: background-color 0.2s;
        }}
        
        tbody tr:hover {{
            background: oklch(from #f9fafb 0.98 0 0);
        }}
        
        .username-link {{
            color: oklch(from #667eea 0.6 0.15 260);
            text-decoration: none;
            font-weight: 600;
            transition: color 0.2s;
        }}
        
        .username-link:hover {{
            color: oklch(from #764ba2 0.5 0.18 300);
            text-decoration: underline;
        }}
        
        .metric-cell {{
            text-align: center;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
            font-size: 0.9em;
        }}
        
        .date-cell {{
            font-weight: 500;
            color: oklch(from #4b5563 0.4 0 0);
        }}
        
        .repo-cell {{
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
            font-size: 0.9em;
            color: oklch(from #6b7280 0.5 0 0);
        }}
        
        .positive {{
            color: oklch(from #10b981 0.55 0.15 150);
        }}
        
        .negative {{
            color: oklch(from #ef4444 0.55 0.2 25);
        }}
        
        .footer {{
            text-align: center;
            color: white;
            margin-top: 30px;
            opacity: 0.9;
            font-size: 0.9em;
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 1.8em;
            }}
            
            table {{
                font-size: 0.85em;
            }}
            
            th, td {{
                padding: 10px 8px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Team Activity Reports</h1>
            <p>Aggregated GitHub repository activity metrics</p>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">{total_reports}</div>
                    <div class="stat-label">Total Reports</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{unique_users}</div>
                    <div class="stat-label">Team Members</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{unique_repos}</div>
                    <div class="stat-label">Repositories</div>
                </div>
            </div>
        </div>
        
        <div class="table-container">
            <h2 style="margin: 0 0 20px 0; color: oklch(from #1f2937 0.3 0 0); font-size: 1.5em;">Summary by User</h2>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Username</th>
                        <th>Real Name</th>
                        <th>Total PRs Merged</th>
                    </tr>
                </thead>
                <tbody>
{summary_rows}
                </tbody>
            </table>
        </div>
        
        <div class="table-container" style="margin-top: 40px;">
            <h2 style="margin: 0 0 20px 0; color: oklch(from #1f2937 0.3 0 0); font-size: 1.5em;">Individual Reports (7 days per repo)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Username</th>
                        <th>Repository</th>
                        <th>PRs Merged</th>
                        <th>Reviews</th>
                        <th>Issues Opened</th>
                        <th>Issues Closed</th>
                        <th>Comments</th>
                        <th>Commits</th>
                        <th>Lines +</th>
                        <th>Lines -</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Calculate summary stats
    unique_users = len(set(r['username'] for r in reports))
    unique_repos = len(set(r['repo'] for r in reports))
    
    # Sort reports alphabetically by username
    sorted_reports = sorted(reports, key=lambda r: r['username'].lower())
    
    # Add rows for each report
    for report in sorted_reports:
        metrics = report['metrics']
        
        # Extract metric values (handle various formats)
        def get_metric_value(label_pattern):
            for key, value in metrics.items():
                if label_pattern in key:
                    # Remove emoji and extra text, get just the number
                    clean_value = re.sub(r'[^\d+\-,]', '', value)
                    return clean_value if clean_value else '0'
            return '0'
        
        prs_merged = get_metric_value('PRs Merged')
        reviews = get_metric_value('Reviews Given')
        issues_opened = get_metric_value('Issues Opened')
        issues_closed = get_metric_value('Issues Closed')
        comments = get_metric_value('Issue Comments') or get_metric_value('Comments')
        commits = get_metric_value('Commits')
        lines_added = get_metric_value('Lines Added')
        lines_deleted = get_metric_value('Lines Deleted')
        
        html += f"""                    <tr>
                        <td class="date-cell">{report['date']}</td>
                        <td><a href="team/{report['filename']}" class="username-link">@{report['username']}</a></td>
                        <td class="repo-cell">{report['repo']}</td>
                        <td class="metric-cell">{prs_merged}</td>
                        <td class="metric-cell">{reviews}</td>
                        <td class="metric-cell">{issues_opened}</td>
                        <td class="metric-cell">{issues_closed}</td>
                        <td class="metric-cell">{comments}</td>
                        <td class="metric-cell">{commits}</td>
                        <td class="metric-cell positive">{lines_added}</td>
                        <td class="metric-cell negative">{lines_deleted}</td>
                    </tr>
"""
    
    html += """                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Generated on {current_date} | Click username to view detailed report</p>
        </div>
    </div>
</body>
</html>
"""
    
    # Load user names mapping
    user_names = {}
    user_names_file = Path(__file__).parent / 'user_names.json'
    if user_names_file.exists():
        try:
            with open(user_names_file, 'r', encoding='utf-8') as f:
                user_names = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load user_names.json: {e}")
    
    # Calculate summary by user
    from collections import defaultdict
    user_summary = defaultdict(lambda: {'prs_merged': 0, 'date': None})
    
    for report in reports:
        username = report['username']
        metrics = report['metrics']
        
        # Extract PRs Merged value
        def get_metric_value(label_pattern):
            for key, value in metrics.items():
                if label_pattern in key:
                    # Remove emoji and extra text, get just the number
                    clean_value = re.sub(r'[^\d]', '', value)
                    return int(clean_value) if clean_value else 0
            return 0
        
        prs_merged = get_metric_value('PRs Merged')
        user_summary[username]['prs_merged'] += prs_merged
        
        # Use the most recent date for this user
        if user_summary[username]['date'] is None or report['date'] > user_summary[username]['date']:
            user_summary[username]['date'] = report['date']
    
    # Generate summary rows
    summary_rows = ""
    for username in sorted(user_summary.keys()):
        summary = user_summary[username]
        real_name = user_names.get(username, username)  # Fall back to username if not found
        summary_rows += f"""                    <tr>
                        <td class="date-cell">{summary['date']}</td>
                        <td>@{username}</td>
                        <td>{real_name}</td>
                        <td class="metric-cell">{summary['prs_merged']}</td>
                    </tr>
"""
    
    # Fill in template variables
    html = html.format(
        total_reports=len(reports),
        unique_users=unique_users,
        unique_repos=unique_repos,
        summary_rows=summary_rows,
        current_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✓ Generated index with {len(reports)} reports")


def main():
    # Define paths
    team_dir = Path(__file__).parent / 'reports' / 'team'
    reports_dir = Path(__file__).parent / 'reports'
    
    # Create directories if they don't exist
    team_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Scanning {team_dir} for reports...")
    
    # Find all HTML files (except index.html)
    html_files = [f for f in team_dir.glob('*.html') if f.name != 'index.html']
    
    if not html_files:
        print("⚠️  No report files found in reports/team/")
        print("Generate reports first, then run this script.")
        return
    
    print(f"Found {len(html_files)} report(s)")
    
    # Parse all reports
    reports = []
    for html_file in html_files:
        print(f"  Parsing {html_file.name}...")
        report_data = parse_report_file(html_file)
        if report_data:
            reports.append(report_data)
    
    if not reports:
        print("⚠️  No valid reports could be parsed")
        return
    
    # Generate index.html in reports/ directory (one level up from team/)
    index_path = reports_dir / 'index.html'
    generate_index_html(reports, index_path)
    
    print(f"\n✨ Index page created: {index_path}")
    print(f"   Open with: open {index_path}")


if __name__ == '__main__':
    main()

