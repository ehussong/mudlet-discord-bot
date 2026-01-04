# bot/services/github_client.py
"""GitHub client for issue creation with PAT and App authentication."""

import logging
from typing import Any, TypedDict

from github import Github

from bot.models.bug_report import BugReport

logger = logging.getLogger(__name__)


class IssueSearchResult(TypedDict):
    """Search result for a GitHub issue."""

    number: int
    title: str
    url: str
    state: str


class GitHubClient:
    """GitHub client for issue creation and management."""

    def __init__(
        self,
        token: str | None = None,
        repo: str = "Mudlet/Mudlet",
        app_id: str | None = None,
        private_key_path: str | None = None,
        installation_id: str | None = None,
    ) -> None:
        """
        Initialize GitHub client with PAT or App authentication.

        Args:
            token: Personal Access Token for authentication
            repo: Repository in "owner/repo" format
            app_id: GitHub App ID (for App auth)
            private_key_path: Path to private key file (for App auth)
            installation_id: GitHub App installation ID (for App auth)

        Raises:
            ValueError: If neither token nor app credentials are provided
            NotImplementedError: If App authentication is attempted
        """
        self._repo_name = repo
        self._labels_cache: list[str] | None = None

        if app_id and private_key_path and installation_id:
            raise NotImplementedError(
                "GitHub App authentication is not yet implemented. "
                "Please use a Personal Access Token instead."
            )
        elif token:
            self._github = Github(token)
            self._repo = self._github.get_repo(repo)
        else:
            raise ValueError(
                "Either token or GitHub App credentials "
                "(app_id, private_key_path, installation_id) must be provided"
            )

    def get_valid_labels(self) -> list[str]:
        """
        Fetch and cache valid labels from the repository.

        Returns:
            List of valid label names from the repository
        """
        if self._labels_cache is not None:
            return self._labels_cache

        labels = self._repo.get_labels()
        self._labels_cache = [label.name for label in labels]
        logger.info(f"Cached {len(self._labels_cache)} labels from {self._repo_name}")
        return self._labels_cache

    def create_issue(self, report: BugReport) -> tuple[str, int]:
        """
        Create a GitHub issue from a bug report.

        Args:
            report: BugReport to create issue from

        Returns:
            Tuple of (issue_url, issue_number)
        """
        # Validate labels against repository labels
        valid_labels = self.get_valid_labels()
        filtered_labels = [label for label in report.labels if label in valid_labels]

        if len(filtered_labels) != len(report.labels):
            invalid = set(report.labels) - set(filtered_labels)
            logger.warning(f"Filtered invalid labels: {invalid}")

        issue = self._repo.create_issue(
            title=report.title,
            body=report.to_github_body(),
            labels=filtered_labels,
        )

        logger.info(f"Created issue #{issue.number}: {issue.html_url}")
        return issue.html_url, issue.number

    def search_issues(self, keywords: list[str], max_results: int = 5) -> list[IssueSearchResult]:
        """
        Search for potential duplicate issues.

        Args:
            keywords: List of keywords to search for
            max_results: Maximum number of results to return

        Returns:
            List of matching issues with number, title, url, and state
        """
        query_terms = " ".join(keywords[:5])  # Limit to 5 keywords
        query = f"{query_terms} repo:{self._repo_name} is:issue"

        logger.info(f"Searching issues with query: {query}")
        issues = self._github.search_issues(query, sort="updated", order="desc")

        results: list[IssueSearchResult] = []
        count = 0
        for item in issues:
            if count >= max_results:
                break
            results.append(
                IssueSearchResult(
                    number=item.number,
                    title=item.title,
                    url=item.html_url,
                    state=item.state,
                )
            )
            count += 1

        logger.info(f"Found {len(results)} potential duplicates")
        return results
