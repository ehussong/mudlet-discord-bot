# tests/test_github_client.py
from unittest.mock import MagicMock, patch

import pytest

from bot.models.bug_report import BugReport
from bot.services.github_client import GitHubClient


@pytest.fixture
def sample_report() -> BugReport:
    return BugReport(
        summary="Test bug report", steps=["Step 1", "Step 2"], error_output="Error here",
        extra_info="Version 1.0", labels=["OS:Windows", "high"], source_channel_id="123",
        source_user_id="456", reporter_name="TestUser",
        discord_link="https://discord.com/channels/1/2/3"
    )


def test_github_client_init_with_token() -> None:
    with patch("bot.services.github_client.Github") as mock_github:
        mock_github.return_value.get_repo.return_value = MagicMock()
        GitHubClient(token="ghp_test123", repo="Test/Repo")
        mock_github.assert_called_once_with("ghp_test123")


def test_github_client_get_valid_labels() -> None:
    mock_label1, mock_label2 = MagicMock(), MagicMock()
    mock_label1.name, mock_label2.name = "OS:Windows", "high"
    with patch("bot.services.github_client.Github") as mock_github:
        mock_repo = MagicMock()
        mock_repo.get_labels.return_value = [mock_label1, mock_label2]
        mock_github.return_value.get_repo.return_value = mock_repo
        client = GitHubClient(token="test", repo="Test/Repo")
        labels = client.get_valid_labels()
        assert "OS:Windows" in labels
        assert "high" in labels


def test_github_client_create_issue(sample_report: BugReport) -> None:
    mock_issue = MagicMock()
    mock_issue.html_url = "https://github.com/Test/Repo/issues/42"
    mock_issue.number = 42
    with patch("bot.services.github_client.Github") as mock_github:
        mock_repo = MagicMock()
        mock_repo.create_issue.return_value = mock_issue
        mock_repo.get_labels.return_value = []
        mock_github.return_value.get_repo.return_value = mock_repo
        client = GitHubClient(token="test", repo="Test/Repo")
        url, number = client.create_issue(sample_report)
        assert url == "https://github.com/Test/Repo/issues/42"
        assert number == 42


def test_github_client_validates_labels_before_applying(sample_report: BugReport) -> None:
    mock_label = MagicMock()
    mock_label.name = "high"  # Only "high" exists
    mock_issue = MagicMock()
    mock_issue.html_url = "https://github.com/Test/Repo/issues/1"
    mock_issue.number = 1
    with patch("bot.services.github_client.Github") as mock_github:
        mock_repo = MagicMock()
        mock_repo.get_labels.return_value = [mock_label]
        mock_repo.create_issue.return_value = mock_issue
        mock_github.return_value.get_repo.return_value = mock_repo
        client = GitHubClient(token="test", repo="Test/Repo")
        client.create_issue(sample_report)
        call_kwargs = mock_repo.create_issue.call_args[1]
        assert call_kwargs["labels"] == ["high"]  # OS:Windows filtered out
