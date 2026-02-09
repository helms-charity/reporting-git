#!/usr/bin/env python3
"""
GitHub Repository User Activity Report Generator

Generates reports for a specific user's activity within a specific repository.
This is more accurate than the Events API for tracking work on specific projects.
"""

import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional
import argparse


class GitHubRepoUserAnalyzer:
    def __init__(self, owner: str, repo: str, username: str, github_token: Optional[str] = None, base_url: Optional[str] = None):
        self.owner = owner
        self.repo = repo
        self.username = username
        self.base_url = (base_url or "").rstrip("/") or "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        if github_token:
            self.headers["Authorization"] = f"Bearer {github_token}"
        
        self.stats = {
            "pull_requests_opened": [],
            "pull_requests_merged": [],
            "pull_requests_closed": [],
            "pull_requests_reviewed": [],
            "issues_opened": [],
            "issues_closed": [],
            "issue_comments": [],
            "commits_authored": [],
            "review_comments_given": 0,
            "total_additions": 0,
            "total_deletions": 0,
            "total_files_changed": 0,
            "pr_sizes": {
                "xs": 0,   # < 10 changes
                "s": 0,    # 10-29 changes
                "m": 0,    # 30-99 changes
                "l": 0,    # 100-499 changes
                "xl": 0,   # 500-999 changes
                "xxl": 0,  # >= 1000 changes
            }
        }
    
    def _get_pr_size(self, changes: int) -> str:
        """Categorize PR size based on total changes (additions + deletions)"""
        if changes < 10:
            return "xs"
        elif changes < 30:
            return "s"
        elif changes < 100:
            return "m"
        elif changes < 500:
            return "l"
        elif changes < 1000:
            return "xl"
        else:
            return "xxl"
    
    def fetch_user_prs(self, since_date: datetime) -> List[Dict]:
        """Fetch PRs created by the user in the repo"""
        print(f"Fetching PRs by @{self.username} in {self.owner}/{self.repo}...")
        
        # Use GitHub Search API for better filtering
        query = f"repo:{self.owner}/{self.repo} is:pr author:{self.username} created:>={since_date.strftime('%Y-%m-%d')}"
        url = f"{self.base_url}/search/issues"
        params = {
            "q": query,
            "sort": "created",
            "order": "desc",
            "per_page": 100
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching PRs: {response.status_code} - {response.text}")
            return []
        
        data = response.json()
        prs = data.get("items", [])
        
        print(f"Found {len(prs)} PRs")
        
        # Get detailed info for each PR
        detailed_prs = []
        for pr_summary in prs:
            pr_number = pr_summary["number"]
            pr_url = f"{self.base_url}/repos/{self.owner}/{self.repo}/pulls/{pr_number}"
            pr_response = requests.get(pr_url, headers=self.headers)
            
            if pr_response.status_code == 200:
                detailed_prs.append(pr_response.json())
        
        return detailed_prs
    
    def fetch_user_closed_issues(self, since_date: datetime) -> List[Dict]:
        """Fetch issues closed by the user in the repo"""
        print(f"Fetching issues closed by @{self.username} in {self.owner}/{self.repo}...")
        
        # Search for issues closed by the user
        query = f"repo:{self.owner}/{self.repo} is:issue is:closed closed:>={since_date.strftime('%Y-%m-%d')}"
        url = f"{self.base_url}/search/issues"
        params = {
            "q": query,
            "sort": "updated",
            "order": "desc",
            "per_page": 100
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching closed issues: {response.status_code}")
            return []
        
        data = response.json()
        all_issues = data.get("items", [])
        
        # Filter to only issues closed by this user
        # GitHub doesn't have a direct "closed-by" search filter, so we need to check events
        user_closed_issues = []
        for issue in all_issues:
            issue_number = issue["number"]
            events_url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues/{issue_number}/events"
            events_response = requests.get(events_url, headers=self.headers)
            
            if events_response.status_code == 200:
                events = events_response.json()
                # Check if this user closed the issue
                for event in events:
                    if event.get("event") == "closed" and event.get("actor", {}).get("login", "").lower() == self.username.lower():
                        # Check if the close event is within our date range
                        created_at = event.get("created_at")
                        if created_at:
                            event_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
                            if event_date >= since_date:
                                user_closed_issues.append(issue)
                                break
        
        print(f"Found {len(user_closed_issues)} issues closed by user")
        
        return user_closed_issues
    
    def fetch_user_reviews(self, since_date: datetime) -> List[Dict]:
        """Fetch reviews given by the user in the repo"""
        print(f"Fetching reviews by @{self.username} in {self.owner}/{self.repo}...")
        
        # Search for PRs where user has reviewed
        # Note: GitHub search doesn't let us filter reviews by date directly,
        # so we search for PRs and then filter the reviews by date
        query = f"repo:{self.owner}/{self.repo} is:pr reviewed-by:{self.username}"
        url = f"{self.base_url}/search/issues"
        
        all_reviews = []
        page = 1
        
        while page <= 3:  # Get up to 300 PRs (3 pages * 100)
            params = {
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": 100,
                "page": page
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                print(f"Error fetching reviewed PRs: {response.status_code}")
                break
            
            data = response.json()
            reviewed_prs = data.get("items", [])
            
            if not reviewed_prs:
                break
            
            print(f"Found {len(reviewed_prs)} PRs on page {page}")
            
            # Get review details for each PR
            for pr in reviewed_prs:
                pr_number = pr["number"]
                reviews_url = f"{self.base_url}/repos/{self.owner}/{self.repo}/pulls/{pr_number}/reviews"
                reviews_response = requests.get(reviews_url, headers=self.headers)
                
                if reviews_response.status_code == 200:
                    reviews = reviews_response.json()
                    # Filter to only this user's reviews
                    user_reviews = [r for r in reviews if r["user"]["login"].lower() == self.username.lower()]
                    for review in user_reviews:
                        review["pr_number"] = pr_number
                        review["pr_title"] = pr["title"]
                        review["pr_url"] = pr["html_url"]
                    all_reviews.extend(user_reviews)
            
            page += 1
        
        print(f"Total reviews found: {len(all_reviews)}")
        return all_reviews
    
    def fetch_user_commits(self, since_date: datetime) -> List[Dict]:
        """Fetch commits authored by the user in the repo"""
        print(f"Fetching commits by @{self.username} in {self.owner}/{self.repo}...")
        
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/commits"
        params = {
            "author": self.username,
            "since": since_date.isoformat(),
            "per_page": 100
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching commits: {response.status_code}")
            return []
        
        commits = response.json()
        print(f"Found {len(commits)} commits")
        
        return commits
    
    def fetch_user_issues(self, since_date: datetime) -> List[Dict]:
        """Fetch issues opened by the user in the repo"""
        print(f"Fetching issues opened by @{self.username} in {self.owner}/{self.repo}...")
        
        # Search for issues (not PRs) created by the user
        query = f"repo:{self.owner}/{self.repo} is:issue author:{self.username} created:>={since_date.strftime('%Y-%m-%d')}"
        url = f"{self.base_url}/search/issues"
        params = {
            "q": query,
            "sort": "created",
            "order": "desc",
            "per_page": 100
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching issues: {response.status_code}")
            return []
        
        data = response.json()
        issues = data.get("items", [])
        
        print(f"Found {len(issues)} issues")
        
        return issues
    
    def fetch_user_issue_comments(self, since_date: datetime) -> List[Dict]:
        """Fetch issue comments made by the user in the repo"""
        print(f"Fetching issue comments by @{self.username} in {self.owner}/{self.repo}...")
        
        # Search for issues (not PRs) where user has commented
        query = f"repo:{self.owner}/{self.repo} is:issue commenter:{self.username}"
        url = f"{self.base_url}/search/issues"
        
        all_comments = []
        page = 1
        
        while page <= 3:  # Get up to 300 issues
            params = {
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": 100,
                "page": page
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                print(f"Error fetching issues with comments: {response.status_code}")
                break
            
            data = response.json()
            issues = data.get("items", [])
            
            if not issues:
                break
            
            print(f"Found {len(issues)} issues with comments on page {page}")
            
            # Get comment details for each issue
            for issue in issues:
                issue_number = issue["number"]
                comments_url = f"{self.base_url}/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments"
                comments_response = requests.get(comments_url, headers=self.headers)
                
                if comments_response.status_code == 200:
                    comments = comments_response.json()
                    # Filter to only this user's comments
                    user_comments = [c for c in comments if c["user"]["login"].lower() == self.username.lower()]
                    for comment in user_comments:
                        comment["issue_number"] = issue_number
                        comment["issue_title"] = issue["title"]
                        comment["issue_url"] = issue["html_url"]
                        comment["issue_state"] = issue["state"]
                    all_comments.extend(user_comments)
            
            page += 1
        
        print(f"Total issue comments found: {len(all_comments)}")
        return all_comments
    
    def analyze_activity(self, days: int, end_date: Optional[datetime] = None):
        """Analyze all user activity in the repository"""
        if end_date is None:
            end_date = datetime.now()
        since_date = end_date - timedelta(days=days)
        
        # Store date range for reporting
        self.end_date = end_date
        self.since_date = since_date
        
        # Fetch PRs
        prs = self.fetch_user_prs(since_date)
        total_commits_in_prs = 0
        for pr in prs:
            additions = pr.get("additions", 0)
            deletions = pr.get("deletions", 0)
            total_changes = additions + deletions
            pr_size = self._get_pr_size(total_changes)
            
            pr_data = {
                "number": pr["number"],
                "title": pr["title"],
                "url": pr["html_url"],
                "state": pr["state"],
                "created_at": pr["created_at"],
                "updated_at": pr["updated_at"],
                "closed_at": pr.get("closed_at"),
                "merged_at": pr.get("merged_at"),
                "additions": additions,
                "deletions": deletions,
                "total_changes": total_changes,
                "size": pr_size,
                "changed_files": pr.get("changed_files", 0),
                "commits": pr.get("commits", 0),
            }
            
            self.stats["pull_requests_opened"].append(pr_data)
            total_commits_in_prs += pr_data["commits"]
            
            # Track PR size distribution
            self.stats["pr_sizes"][pr_size] += 1
            
            if pr.get("merged_at"):
                self.stats["pull_requests_merged"].append(pr_data)
            elif pr["state"] == "closed":
                self.stats["pull_requests_closed"].append(pr_data)
            
            self.stats["total_additions"] += additions
            self.stats["total_deletions"] += deletions
            self.stats["total_files_changed"] += pr_data["changed_files"]
        
        # Store total commits in PRs
        self.stats["total_commits_in_prs"] = total_commits_in_prs
        
        # Fetch reviews
        reviews = self.fetch_user_reviews(since_date)
        for review in reviews:
            # Filter by review submission date
            submitted_at = review.get("submitted_at")
            if submitted_at:
                review_date = datetime.strptime(submitted_at, "%Y-%m-%dT%H:%M:%SZ")
                if review_date < since_date:
                    continue  # Skip reviews outside the date range
            
            review_data = {
                "pr_number": review["pr_number"],
                "pr_title": review["pr_title"],
                "pr_url": review["pr_url"],
                "state": review["state"],
                "submitted_at": submitted_at,
                "body": review.get("body", "")[:200],
            }
            self.stats["pull_requests_reviewed"].append(review_data)
        
        # Count review statistics
        self.stats["total_reviews_given"] = len(self.stats["pull_requests_reviewed"])
        self.stats["unique_prs_reviewed"] = len(set(r["pr_number"] for r in self.stats["pull_requests_reviewed"]))
        
        # Fetch issues opened
        issues = self.fetch_user_issues(since_date)
        for issue in issues:
            issue_data = {
                "number": issue["number"],
                "title": issue["title"],
                "url": issue["html_url"],
                "state": issue["state"],
                "created_at": issue["created_at"],
                "updated_at": issue["updated_at"],
                "closed_at": issue.get("closed_at"),
                "comments_count": issue.get("comments", 0),
            }
            self.stats["issues_opened"].append(issue_data)
        
        # Fetch issues closed
        closed_issues = self.fetch_user_closed_issues(since_date)
        for issue in closed_issues:
            issue_data = {
                "number": issue["number"],
                "title": issue["title"],
                "url": issue["html_url"],
                "state": issue["state"],
                "created_at": issue.get("created_at"),
                "closed_at": issue.get("closed_at"),
                "comments_count": issue.get("comments", 0),
            }
            self.stats["issues_closed"].append(issue_data)
        
        # Fetch issue comments
        issue_comments = self.fetch_user_issue_comments(since_date)
        for comment in issue_comments:
            # Filter by comment creation date
            created_at = comment.get("created_at")
            if created_at:
                comment_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
                if comment_date < since_date:
                    continue  # Skip comments outside the date range
            
            comment_data = {
                "issue_number": comment["issue_number"],
                "issue_title": comment["issue_title"],
                "issue_url": comment["issue_url"],
                "issue_state": comment["issue_state"],
                "created_at": created_at,
                "body": comment.get("body", "")[:200],
            }
            self.stats["issue_comments"].append(comment_data)
        
        # Fetch commits (direct commits, not in PRs)
        commits = self.fetch_user_commits(since_date)
        for commit in commits:
            commit_data = {
                "sha": commit["sha"][:7],
                "message": commit["commit"]["message"].split('\n')[0],
                "date": commit["commit"]["author"]["date"],
                "url": commit["html_url"],
            }
            self.stats["commits_authored"].append(commit_data)
    
    def generate_report(self, days: int, format: str = "text") -> str:
        """Generate report in specified format"""
        if format == "text":
            return self._generate_text_report(days)
        elif format == "html":
            return self._generate_html_report(days)
        elif format == "json":
            return self._generate_json_report()
    
    def _generate_text_report(self, days: int) -> str:
        """Generate text report"""
        report = []
        report.append("=" * 80)
        report.append(f"Repository Activity Report")
        report.append(f"Repository: {self.owner}/{self.repo}")
        report.append(f"User: @{self.username}")
        
        # Show date range if available
        if hasattr(self, 'since_date') and hasattr(self, 'end_date'):
            report.append(f"Period: {self.since_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')} ({days} days)")
        else:
            report.append(f"Period: Last {days} days")
        
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        report.append("")
        
        # Summary Statistics
        report.append("📊 SUMMARY STATISTICS")
        report.append("-" * 80)
        total_prs = len(self.stats['pull_requests_opened'])
        total_merged = len(self.stats['pull_requests_merged'])
        report.append(f"Pull Requests Merged:     {total_merged}")
        report.append(f"Reviews Given:            {self.stats.get('total_reviews_given', len(self.stats['pull_requests_reviewed']))}")
        unique_prs = self.stats.get('unique_prs_reviewed', len(set(r['pr_number'] for r in self.stats['pull_requests_reviewed'])))
        report.append(f"Unique PRs Reviewed:      {unique_prs}")
        report.append(f"Issues Opened:            {len(self.stats['issues_opened'])}")
        report.append(f"Issues Closed:            {len(self.stats['issues_closed'])}")
        report.append(f"Issue Comments:           {len(self.stats['issue_comments'])}")
        unique_issues = len(set(c['issue_number'] for c in self.stats['issue_comments']))
        report.append(f"Unique Issues Commented:  {unique_issues}")
        report.append(f"Commits in PRs:           {self.stats.get('total_commits_in_prs', 0)}")
        report.append(f"Direct Commits:           {len(self.stats['commits_authored'])}")
        report.append(f"Total Lines Added:        +{self.stats['total_additions']}")
        report.append(f"Total Lines Deleted:      -{self.stats['total_deletions']}")
        report.append(f"Total Files Changed:      {self.stats['total_files_changed']}")
        report.append("")
        
        # PR Size Distribution
        report.append("📏 PULL REQUEST SIZE DISTRIBUTION")
        report.append("-" * 80)
        report.append(f"XS  (< 10 changes):       {self.stats['pr_sizes']['xs']}")
        report.append(f"S   (10-29 changes):      {self.stats['pr_sizes']['s']}")
        report.append(f"M   (30-99 changes):      {self.stats['pr_sizes']['m']}")
        report.append(f"L   (100-499 changes):    {self.stats['pr_sizes']['l']}")
        report.append(f"XL  (500-999 changes):    {self.stats['pr_sizes']['xl']}")
        report.append(f"XXL (≥ 1000 changes):     {self.stats['pr_sizes']['xxl']}")
        report.append("")
        
        # Pull Requests Opened
        if self.stats["pull_requests_opened"]:
            report.append(f"🔀 PULL REQUESTS OPENED ({len(self.stats['pull_requests_opened'])})")
            report.append("-" * 80)
            for pr in self.stats["pull_requests_opened"]:
                status = "✅ Merged" if pr.get("merged_at") else ("❌ Closed" if pr["state"] == "closed" else "🔄 Open")
                size = pr.get('size', 'm').upper()
                report.append(f"  {status} [{size}] #{pr['number']}: {pr['title']}")
                report.append(f"    URL: {pr['url']}")
                report.append(f"    Stats: +{pr['additions']} -{pr['deletions']} lines "
                            f"({pr.get('total_changes', pr['additions'] + pr['deletions'])} total changes), "
                            f"{pr['changed_files']} files, {pr['commits']} commits")
                report.append(f"    Created: {pr['created_at']}")
                if pr.get("merged_at"):
                    report.append(f"    Merged: {pr['merged_at']}")
                report.append("")
        
        # Pull Requests Reviewed
        if self.stats["pull_requests_reviewed"]:
            unique_count = len(set(r["pr_number"] for r in self.stats["pull_requests_reviewed"]))
            report.append(f"👀 PULL REQUESTS REVIEWED ({len(self.stats['pull_requests_reviewed'])} reviews on {unique_count} PRs)")
            report.append("-" * 80)
            
            for review in self.stats["pull_requests_reviewed"]:
                report.append(f"  • {review['state'].upper()} on #{review['pr_number']}: {review['pr_title']}")
                report.append(f"    URL: {review['pr_url']}")
                report.append(f"    Submitted: {review.get('submitted_at') or 'Unknown'}")
                report.append("")
        
        # Issues Opened
        if self.stats["issues_opened"]:
            report.append(f"🐛 ISSUES OPENED ({len(self.stats['issues_opened'])})")
            report.append("-" * 80)
            for issue in self.stats["issues_opened"]:
                status = "🔓 Open" if issue["state"] == "open" else "✅ Closed"
                report.append(f"  {status} #{issue['number']}: {issue['title']}")
                report.append(f"    URL: {issue['url']}")
                report.append(f"    Created: {issue['created_at']}")
                report.append(f"    Comments: {issue['comments_count']}")
                if issue.get("closed_at"):
                    report.append(f"    Closed: {issue['closed_at']}")
                report.append("")
        
        # Issues Closed
        if self.stats["issues_closed"]:
            report.append(f"✅ ISSUES CLOSED BY USER ({len(self.stats['issues_closed'])})")
            report.append("-" * 80)
            for issue in self.stats["issues_closed"]:
                report.append(f"  ✅ #{issue['number']}: {issue['title']}")
                report.append(f"    URL: {issue['url']}")
                if issue.get("closed_at"):
                    report.append(f"    Closed: {issue['closed_at']}")
                report.append(f"    Comments: {issue['comments_count']}")
                report.append("")
        
        # Issue Comments
        if self.stats["issue_comments"]:
            unique_issues_count = len(set(c["issue_number"] for c in self.stats["issue_comments"]))
            report.append(f"💬 ISSUE COMMENTS ({len(self.stats['issue_comments'])} comments on {unique_issues_count} issues)")
            report.append("-" * 80)
            
            for comment in self.stats["issue_comments"]:
                status = "🔓 Open" if comment["issue_state"] == "open" else "✅ Closed"
                report.append(f"  • {status} #{comment['issue_number']}: {comment['issue_title']}")
                report.append(f"    URL: {comment['issue_url']}")
                report.append(f"    Commented: {comment['created_at']}")
                report.append(f"    Preview: {comment['body'][:100]}...")
                report.append("")
        
        # Commits
        if self.stats["commits_authored"]:
            report.append(f"💾 DIRECT COMMITS ({len(self.stats['commits_authored'])})")
            report.append("-" * 80)
            report.append("Note: These are direct commits. Commits in PRs are shown above.")
            report.append("")
            for commit in self.stats["commits_authored"][:10]:  # Show first 10
                report.append(f"  • {commit['sha']}: {commit['message']}")
                report.append(f"    {commit['date']}")
            if len(self.stats["commits_authored"]) > 10:
                report.append(f"  ... and {len(self.stats['commits_authored']) - 10} more")
            report.append("")
        
        return "\n".join(report)
    
    def _generate_html_report(self, days: int) -> str:
        """Generate HTML report with modern styling"""
        total_prs = len(self.stats['pull_requests_opened'])
        total_merged = len(self.stats['pull_requests_merged'])
        total_reviews = self.stats.get('total_reviews_given', len(self.stats['pull_requests_reviewed']))
        unique_prs_reviewed = self.stats.get('unique_prs_reviewed', len(set(r['pr_number'] for r in self.stats['pull_requests_reviewed'])))
        total_issues_opened = len(self.stats['issues_opened'])
        total_issues_closed = len(self.stats['issues_closed'])
        total_issue_comments = len(self.stats['issue_comments'])
        unique_issues_commented = len(set(c['issue_number'] for c in self.stats['issue_comments']))
        total_commits = len(self.stats['commits_authored'])
        total_commits_in_prs = self.stats.get('total_commits_in_prs', 0)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Repository Activity Report - @{self.username}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: oklch(from #24292f l c h);
            background: linear-gradient(135deg, oklch(from #f6f8fa l c h) 0%, oklch(from #ffffff l c h) 100%);
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px oklch(from #000000 l c h / 0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, oklch(from #0366d6 l c h) 0%, oklch(from #0969da l c h) 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        .header .repo {{
            font-size: 1.5em;
            margin-bottom: 10px;
            opacity: 0.95;
            font-family: 'Monaco', monospace;
        }}
        
        .header .username {{
            font-size: 1.3em;
            margin-bottom: 15px;
            opacity: 0.9;
        }}
        
        .header .meta {{
            font-size: 0.95em;
            opacity: 0.85;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 40px;
            background: oklch(from #f8f9fa l c h);
        }}
        
        .metric-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            border: 2px solid oklch(from #e9ecef l c h);
            transition: all 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 15px oklch(from #000000 l c h / 0.1);
            border-color: oklch(from #0366d6 l c h);
        }}
        
        .metric-value {{
            font-size: 3em;
            font-weight: 700;
            margin: 10px 0;
            background: linear-gradient(135deg, oklch(from #0366d6 l c h), oklch(from #0969da l c h));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .metric-label {{
            color: oklch(from #6c757d l c h);
            font-size: 0.95em;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
        }}
        
        .section {{
            padding: 40px;
        }}
        
        .section-title {{
            font-size: 1.8em;
            margin-bottom: 25px;
            color: oklch(from #1f2937 l c h);
            border-bottom: 3px solid oklch(from #0366d6 l c h);
            padding-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .pr-card {{
            background: white;
            border: 1px solid oklch(from #e9ecef l c h);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }}
        
        .pr-card:hover {{
            box-shadow: 0 4px 12px oklch(from #000000 l c h / 0.1);
            border-color: oklch(from #0366d6 l c h);
        }}
        
        .pr-title {{
            font-size: 1.2em;
            font-weight: 600;
            color: oklch(from #1f2937 l c h);
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .pr-number {{
            color: oklch(from #0366d6 l c h);
            font-weight: 700;
        }}
        
        .pr-stats {{
            display: flex;
            gap: 20px;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid oklch(from #e9ecef l c h);
            flex-wrap: wrap;
        }}
        
        .pr-stat {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 0.9em;
        }}
        
        .stat-additions {{
            color: oklch(from #22c55e l c h);
            font-weight: 600;
        }}
        
        .stat-deletions {{
            color: oklch(from #ef4444 l c h);
            font-weight: 600;
        }}
        
        .pr-link {{
            color: oklch(from #0366d6 l c h);
            text-decoration: none;
            font-weight: 500;
        }}
        
        .pr-link:hover {{
            text-decoration: underline;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .badge-merged {{
            background: oklch(from #22c55e l c h / 0.1);
            color: oklch(from #16a34a l c h);
        }}
        
        .badge-open {{
            background: oklch(from #3b82f6 l c h / 0.1);
            color: oklch(from #2563eb l c h);
        }}
        
        .badge-closed {{
            background: oklch(from #ef4444 l c h / 0.1);
            color: oklch(from #dc2626 l c h);
        }}
        
        .badge-approved {{
            background: oklch(from #22c55e l c h / 0.1);
            color: oklch(from #16a34a l c h);
        }}
        
        .badge-changes-requested {{
            background: oklch(from #ef4444 l c h / 0.1);
            color: oklch(from #dc2626 l c h);
        }}
        
        .badge-commented {{
            background: oklch(from #3b82f6 l c h / 0.1);
            color: oklch(from #2563eb l c h);
        }}
        
        .badge-size {{
            font-size: 0.75em;
            padding: 3px 8px;
            margin-left: 8px;
        }}
        
        .badge-xs {{
            background: oklch(from #10b981 l c h / 0.15);
            color: oklch(from #059669 l c h);
        }}
        
        .badge-s {{
            background: oklch(from #3b82f6 l c h / 0.15);
            color: oklch(from #2563eb l c h);
        }}
        
        .badge-m {{
            background: oklch(from #f59e0b l c h / 0.15);
            color: oklch(from #d97706 l c h);
        }}
        
        .badge-l {{
            background: oklch(from #f97316 l c h / 0.15);
            color: oklch(from #ea580c l c h);
        }}
        
        .badge-xl {{
            background: oklch(from #ef4444 l c h / 0.15);
            color: oklch(from #dc2626 l c h);
        }}
        
        .badge-xxl {{
            background: oklch(from #991b1b l c h / 0.2);
            color: oklch(from #7f1d1d l c h);
            font-weight: 700;
        }}
        
        .pr-size-chart {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        
        .size-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border: 2px solid oklch(from #e9ecef l c h);
        }}
        
        .size-label {{
            font-size: 0.85em;
            color: oklch(from #6c757d l c h);
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        
        .size-value {{
            font-size: 2.5em;
            font-weight: 700;
            margin: 5px 0;
        }}
        
        .size-description {{
            font-size: 0.75em;
            color: oklch(from #6c757d l c h);
            margin-top: 5px;
        }}
        
        .commit-list {{
            background: oklch(from #f8f9fa l c h);
            border-radius: 8px;
            padding: 20px;
        }}
        
        .commit-item {{
            padding: 10px;
            border-left: 3px solid oklch(from #0366d6 l c h);
            margin-bottom: 10px;
            background: white;
            border-radius: 4px;
        }}
        
        .commit-sha {{
            font-family: 'Monaco', monospace;
            color: oklch(from #0366d6 l c h);
            font-weight: 600;
        }}
        
        .commit-message {{
            margin: 5px 0;
            color: oklch(from #1f2937 l c h);
        }}
        
        .commit-date {{
            font-size: 0.85em;
            color: oklch(from #6c757d l c h);
        }}
        
        @media (max-width: 768px) {{
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
            
            .header h1 {{
                font-size: 1.8em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Repository Activity Report</h1>
            <div class="repo">{self.owner}/{self.repo}</div>
            <div class="username">@{self.username}</div>
            <div class="meta">"""
        
        # Show date range if available
        if hasattr(self, 'since_date') and hasattr(self, 'end_date'):
            html += f"""
                📅 Period: {self.since_date.strftime('%B %d, %Y')} to {self.end_date.strftime('%B %d, %Y')} ({days} days) | """
        else:
            html += f"""
                📅 Period: Last {days} days | """
        
        html += f"""
                🕐 Generated: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}
            </div>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card" style="background: yellow">
                <div class="metric-label">✅ PRs Merged</div>
                <div class="metric-value">{total_merged}</div>
            </div>
            <div class="metric-card" style="background: transparent">
                <div class="metric-label">📈 Lines Added</div>
                <div class="metric-value">+{self.stats['total_additions']}</div>
            </div>
            <div class="metric-card" style="background: transparent">
                <div class="metric-label">📉 Lines Deleted</div>
                <div class="metric-value">-{self.stats['total_deletions']}</div>
            </div>
            <div class="metric-card" style="background: transparent">
                <div class="metric-label">💾 Commits in PRs</div>
                <div class="metric-value">{total_commits_in_prs}</div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">
                <span>📏</span>
                Pull Request Size Distribution
            </h2>
            <p style="color: #6c757d; margin-bottom: 20px; font-size: 0.95em;">
                <em>Based on total changes (additions + deletions). Size categories match OSSInsight standards.</em>
            </p>
            <div class="pr-size-chart">
                <div class="size-card">
                    <div class="size-label">
                        <span class="badge badge-xs badge-size">XS</span>
                    </div>
                    <div class="size-value" style="color: oklch(from #10b981 l c h);">{self.stats['pr_sizes']['xs']}</div>
                    <div class="size-description">&lt; 10 changes</div>
                </div>
                <div class="size-card">
                    <div class="size-label">
                        <span class="badge badge-s badge-size">S</span>
                    </div>
                    <div class="size-value" style="color: oklch(from #3b82f6 l c h);">{self.stats['pr_sizes']['s']}</div>
                    <div class="size-description">10-29 changes</div>
                </div>
                <div class="size-card">
                    <div class="size-label">
                        <span class="badge badge-m badge-size">M</span>
                    </div>
                    <div class="size-value" style="color: oklch(from #f59e0b l c h);">{self.stats['pr_sizes']['m']}</div>
                    <div class="size-description">30-99 changes</div>
                </div>
                <div class="size-card">
                    <div class="size-label">
                        <span class="badge badge-l badge-size">L</span>
                    </div>
                    <div class="size-value" style="color: oklch(from #f97316 l c h);">{self.stats['pr_sizes']['l']}</div>
                    <div class="size-description">100-499 changes</div>
                </div>
                <div class="size-card">
                    <div class="size-label">
                        <span class="badge badge-xl badge-size">XL</span>
                    </div>
                    <div class="size-value" style="color: oklch(from #ef4444 l c h);">{self.stats['pr_sizes']['xl']}</div>
                    <div class="size-description">500-999 changes</div>
                </div>
                <div class="size-card">
                    <div class="size-label">
                        <span class="badge badge-xxl badge-size">XXL</span>
                    </div>
                    <div class="size-value" style="color: oklch(from #991b1b l c h);">{self.stats['pr_sizes']['xxl']}</div>
                    <div class="size-description">≥ 1000 changes</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">
                <span>🤝</span>
                Other repository collaboration
            </h2>
            <p style="color: #6c757d; margin-bottom: 20px; font-size: 0.95em;">
                <em>Authoring, QA-related work, documentation and general collab can be represented here.</em>
            </p>
                <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">👀 Reviews Given</div>
                <div class="metric-value">{total_reviews}</div>
                <div class="size-description">{unique_prs_reviewed} unique PRs</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">🐛 Issues Opened</div>
                <div class="metric-value">{total_issues_opened}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">✅ Issues Closed</div>
                <div class="metric-value">{total_issues_closed}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">💬 Issue Comments</div>
                <div class="metric-value">{total_issue_comments}</div>
                <div class="size-description">{unique_issues_commented} unique issues</div>
            </div>
        </div>
        </div>
"""
        
        # Pull Requests Section
        if self.stats["pull_requests_opened"]:
            html += f"""
        <div class="section">
            <h2 class="section-title">
                <span>🔀</span>
                Pull Requests Opened ({len(self.stats['pull_requests_opened'])})
            </h2>
"""
            for pr in self.stats["pull_requests_opened"]:
                if pr.get("merged_at"):
                    status_badge = '<span class="badge badge-merged">✅ Merged</span>'
                elif pr["state"] == "closed":
                    status_badge = '<span class="badge badge-closed">❌ Closed</span>'
                else:
                    status_badge = '<span class="badge badge-open">🔄 Open</span>'
                
                # Add size badge
                pr_size = pr.get('size', 'm').upper()
                size_badge_class = f"badge-{pr.get('size', 'm')}"
                size_badge = f'<span class="badge {size_badge_class} badge-size">{pr_size}</span>'
                
                pr_date = datetime.strptime(pr['created_at'], "%Y-%m-%dT%H:%M:%SZ").strftime('%B %d, %Y')
                
                html += f"""
            <div class="pr-card">
                <div class="pr-title">
                    <span class="pr-number">#{pr['number']}</span>
                    <a href="{pr['url']}" class="pr-link" target="_blank">{pr['title']}</a>
                    {status_badge}
                    {size_badge}
                </div>
                <div class="pr-stats">
                    <div class="pr-stat">📅 {pr_date}</div>
                    <div class="pr-stat">
                        <span class="stat-additions">+{pr['additions']}</span>
                    </div>
                    <div class="pr-stat">
                        <span class="stat-deletions">-{pr['deletions']}</span>
                    </div>
                    <div class="pr-stat">📊 {pr.get('total_changes', pr['additions'] + pr['deletions'])} total changes</div>
                    <div class="pr-stat">📄 {pr['changed_files']} files</div>
                    <div class="pr-stat">💾 {pr['commits']} commits</div>
                </div>
            </div>
"""
            html += "        </div>\n"
        
        # Issues Closed Section
        if self.stats["issues_closed"]:
            html += f"""
        <div class="section">
            <h2 class="section-title">
                <span>✅</span>
                Issues Closed by {self.username} ({len(self.stats['issues_closed'])})
            </h2>
"""
            for issue in self.stats["issues_closed"]:
                closed_date = datetime.strptime(issue['closed_at'], "%Y-%m-%dT%H:%M:%SZ").strftime('%B %d, %Y') if issue.get('closed_at') else 'Unknown'
                
                html += f"""
            <div class="pr-card">
                <div class="pr-title">
                    <span class="pr-number">#{issue['number']}</span>
                    <a href="{issue['url']}" class="pr-link" target="_blank">{issue['title']}</a>
                    <span class="badge badge-closed">✅ Closed</span>
                </div>
                <div class="pr-stats">
                    <div class="pr-stat">🔒 Closed: {closed_date}</div>
                    <div class="pr-stat">💬 {issue['comments_count']} comments</div>
                </div>
            </div>
"""
            html += "        </div>\n"
        
        # Reviews Section
        if self.stats["pull_requests_reviewed"]:
            html += f"""
        <div class="section">
            <h2 class="section-title">
                <span>👀</span>
                Pull Requests Reviewed ({len(self.stats["pull_requests_reviewed"])} reviews on {unique_prs_reviewed} PRs)
            </h2>
            <p style="color: #6c757d; margin-bottom: 20px; font-size: 0.95em;">
                <em>Showing all reviews. You may have reviewed some PRs multiple times.</em>
            </p>
"""
            for review in self.stats["pull_requests_reviewed"]:
                review_state = review['state'].upper()
                badge_class = {
                    'APPROVED': 'badge-approved',
                    'CHANGES_REQUESTED': 'badge-changes-requested',
                    'COMMENTED': 'badge-commented'
                }.get(review_state, 'badge-commented')
                
                submitted_at = review.get('submitted_at')
                if submitted_at:
                    review_date = datetime.strptime(submitted_at, "%Y-%m-%dT%H:%M:%SZ").strftime('%B %d, %Y')
                else:
                    review_date = "Unknown"
                
                html += f"""
            <div class="pr-card">
                <div class="pr-title">
                    <span class="pr-number">#{review['pr_number']}</span>
                    <a href="{review['pr_url']}" class="pr-link" target="_blank">{review['pr_title']}</a>
                    <span class="badge {badge_class}">{review_state}</span>
                </div>
                <div class="pr-stats">
                    <div class="pr-stat">📅 {review_date}</div>
                </div>
            </div>
"""
            html += "        </div>\n"
        
        # Issues Section
        if self.stats["issues_opened"]:
            html += f"""
        <div class="section">
            <h2 class="section-title">
                <span>🐛</span>
                Issues Opened ({len(self.stats["issues_opened"])})
            </h2>
"""
            for issue in self.stats["issues_opened"]:
                status_badge = '<span class="badge badge-open">🔓 Open</span>' if issue["state"] == "open" else '<span class="badge badge-closed">✅ Closed</span>'
                issue_date = datetime.strptime(issue['created_at'], "%Y-%m-%dT%H:%M:%SZ").strftime('%B %d, %Y')
                
                html += f"""
            <div class="pr-card">
                <div class="pr-title">
                    <span class="pr-number">#{issue['number']}</span>
                    <a href="{issue['url']}" class="pr-link" target="_blank">{issue['title']}</a>
                    {status_badge}
                </div>
                <div class="pr-stats">
                    <div class="pr-stat">📅 {issue_date}</div>
                    <div class="pr-stat">💬 {issue['comments_count']} comments</div>
                </div>
            </div>
"""
            html += "        </div>\n"
        
        # Issue Comments Section
        if self.stats["issue_comments"]:
            unique_issues = len(set(c['issue_number'] for c in self.stats['issue_comments']))
            html += f"""
        <div class="section">
            <h2 class="section-title">
                <span>💬</span>
                Issue Comments ({len(self.stats["issue_comments"])} comments on {unique_issues} issues)
            </h2>
            <p style="color: #6c757d; margin-bottom: 20px; font-size: 0.95em;">
                <em>Showing all comments. You may have commented on some issues multiple times.</em>
            </p>
"""
            for comment in self.stats["issue_comments"]:
                status_badge = '<span class="badge badge-open">🔓 Open</span>' if comment["issue_state"] == "open" else '<span class="badge badge-closed">✅ Closed</span>'
                comment_date = datetime.strptime(comment['created_at'], "%Y-%m-%dT%H:%M:%SZ").strftime('%B %d, %Y')
                comment_preview = comment['body'][:100] + '...' if len(comment['body']) > 100 else comment['body']
                
                html += f"""
            <div class="pr-card">
                <div class="pr-title">
                    <span class="pr-number">#{comment['issue_number']}</span>
                    <a href="{comment['issue_url']}" class="pr-link" target="_blank">{comment['issue_title']}</a>
                    {status_badge}
                </div>
                <div class="pr-stats">
                    <div class="pr-stat">📅 {comment_date}</div>
                </div>
                <div style="margin-top: 10px; padding: 10px; background: oklch(from #f8f9fa l c h); border-radius: 4px; font-size: 0.9em; color: oklch(from #495057 l c h);">
                    {comment_preview}
                </div>
            </div>
"""
            html += "        </div>\n"
        
        # Commits Section (only show if we have direct commits)
        if self.stats["commits_authored"]:
            html += f"""
        <div class="section">
            <h2 class="section-title">
                <span>💾</span>
                Direct Commits ({len(self.stats['commits_authored'])})
            </h2>
            <p style="color: #6c757d; margin-bottom: 20px; font-size: 0.95em;">
                <em>Note: These are direct commits to the repository. Commits within PRs are shown in the PR cards above.</em>
            </p>
            <div class="commit-list">
"""
            for commit in self.stats["commits_authored"][:15]:  # Show first 15
                commit_date = datetime.strptime(commit['date'], "%Y-%m-%dT%H:%M:%SZ").strftime('%b %d, %Y %H:%M')
                html += f"""
                <div class="commit-item">
                    <div>
                        <a href="{commit['url']}" class="commit-sha" target="_blank">{commit['sha']}</a>
                        <span class="commit-message">{commit['message']}</span>
                    </div>
                    <div class="commit-date">{commit_date}</div>
                </div>
"""
            if len(self.stats["commits_authored"]) > 15:
                html += f"<p style='text-align: center; margin-top: 20px; color: #6c757d;'>... and {len(self.stats['commits_authored']) - 15} more commits</p>"
            
            html += """
            </div>
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        return html
    
    def _generate_json_report(self) -> str:
        """Generate JSON report"""
        return json.dumps(self.stats, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(
        description="Generate activity reports for a user within a specific repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Weekly report for helms-charity in aemsites/idfc
  python github_repo_user_report.py aemsites idfc helms-charity --days 7
  
  # Monthly HTML report
  python github_repo_user_report.py aemsites idfc helms-charity --days 30 --format html --output report.html
  
  # Report for specific date range (7 days ending on 2026-01-31)
  python github_repo_user_report.py aemsites idfc helms-charity --days 7 --startdate 2026-01-31
  
  # With GitHub token for higher rate limits
  export GITHUB_TOKEN=your_token_here
  python github_repo_user_report.py aemsites idfc helms-charity --token $GITHUB_TOKEN
        """
    )
    
    parser.add_argument("owner", help="Repository owner (e.g., 'aemsites')")
    parser.add_argument("repo", help="Repository name (e.g., 'idfc')")
    parser.add_argument("username", help="GitHub username to analyze")
    parser.add_argument("--days", type=int, default=7, 
                       help="Number of days to analyze (default: 7)")
    parser.add_argument("--startdate", type=str, 
                       help="End date for analysis in YYYY-MM-DD format (default: today). Use with --days to get period ending on this date.")
    parser.add_argument("--format", choices=["text", "html", "json"], default="text",
                       help="Output format (default: text)")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--token", help="GitHub personal access token (or set GITHUB_TOKEN / GITHUB_ENTERPRISE_TOKEN env var)")
    parser.add_argument("--api-url", help="GitHub API base URL for Enterprise (e.g. https://github.corp.example.com/api/v3). Or set GITHUB_API_URL.")
    
    args = parser.parse_args()
    
    import os
    # API URL: --api-url wins, then env GITHUB_API_URL, else default (github.com)
    api_url = args.api_url or os.environ.get("GITHUB_API_URL")
    # Token: --token wins; if using Enterprise API URL, try GITHUB_ENTERPRISE_TOKEN then GITHUB_TOKEN; else GITHUB_TOKEN only
    token = args.token
    if not token:
        if api_url:
            token = os.environ.get("GITHUB_ENTERPRISE_TOKEN") or os.environ.get("GITHUB_TOKEN")
        else:
            token = os.environ.get("GITHUB_TOKEN")
    
    if not token:
        print("⚠️  Warning: No GitHub token provided. Rate limits will be lower (60 requests/hour).")
        print("   Set GITHUB_TOKEN (or GITHUB_ENTERPRISE_TOKEN for --api-url) or use --token.\n")
    
    # Parse startdate if provided
    end_date = None
    if args.startdate:
        try:
            end_date = datetime.strptime(args.startdate, "%Y-%m-%d")
            print(f"📅 Analyzing from {(end_date - timedelta(days=args.days)).strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        except ValueError:
            print(f"❌ Error: Invalid date format '{args.startdate}'. Use YYYY-MM-DD format.")
            return
    
    # Create analyzer
    analyzer = GitHubRepoUserAnalyzer(args.owner, args.repo, args.username, token, base_url=api_url)
    
    # Analyze activity
    analyzer.analyze_activity(args.days, end_date)
    
    # Generate report
    report = analyzer.generate_report(days=args.days, format=args.format)
    
    # Output report
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"\nReport saved to: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()

