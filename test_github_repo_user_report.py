import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from github_repo_user_report import GitHubRepoUserAnalyzer


class MockResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


class GitHubRepoUserAnalyzerIssueTests(unittest.TestCase):
    def test_fetch_user_issues_counts_closed_authored_issues(self):
        analyzer = GitHubRepoUserAnalyzer("example", "repo", "helms-charity")
        calls = []
        payload = [
            {
                "number": 5,
                "title": "Closed by a PR",
                "html_url": "https://github.com/example/repo/issues/5",
                "state": "closed",
                "created_at": "2026-05-04T12:00:00Z",
                "updated_at": "2026-05-04T13:00:00Z",
                "closed_at": "2026-05-04T13:00:00Z",
                "comments": 0,
                "user": {"login": "helms-charity"},
            },
            {
                "number": 6,
                "title": "PR row from issues API",
                "html_url": "https://github.com/example/repo/pull/6",
                "state": "closed",
                "created_at": "2026-05-04T12:00:00Z",
                "updated_at": "2026-05-04T13:00:00Z",
                "closed_at": "2026-05-04T13:00:00Z",
                "comments": 0,
                "pull_request": {"url": "https://api.github.com/repos/example/repo/pulls/6"},
                "user": {"login": "helms-charity"},
            },
            {
                "number": 7,
                "title": "Different author",
                "html_url": "https://github.com/example/repo/issues/7",
                "state": "open",
                "created_at": "2026-05-04T12:00:00Z",
                "updated_at": "2026-05-04T13:00:00Z",
                "closed_at": None,
                "comments": 0,
                "user": {"login": "someone-else"},
            },
        ]

        def fake_get(url, headers=None, params=None):
            calls.append((url, params))
            return MockResponse(200, payload)

        with patch("github_repo_user_report.requests.get", side_effect=fake_get):
            issues = analyzer.fetch_user_issues(
                datetime(2026, 5, 1, tzinfo=timezone.utc),
                datetime(2026, 5, 8, tzinfo=timezone.utc),
            )

        self.assertEqual([issue["number"] for issue in issues], [5])
        self.assertEqual(calls[0][0], "https://api.github.com/repos/example/repo/issues")
        self.assertEqual(calls[0][1]["state"], "all")
        self.assertEqual(calls[0][1]["creator"], "helms-charity")
        self.assertEqual(calls[0][1]["sort"], "created")


if __name__ == "__main__":
    unittest.main()
