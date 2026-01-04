# tests/test_bug_report.py
from bot.models.bug_report import BugReport


def test_bug_report_to_github_body() -> None:
    """BugReport should format to Mudlet's GitHub issue template."""
    report = BugReport(
        summary="Mapper crashes when adding room to large areas",
        steps=["Open area with >500 rooms", "Try to add a new room", "Mapper crashes"],
        error_output="Segfault at 0x7fff5fbff8c0",
        extra_info="Mudlet 4.18.0, Windows 11",
        labels=["OS:Windows", "mapper bug", "high"],
        source_channel_id="123456789",
        source_user_id="987654321",
        discord_link="https://discord.com/channels/123/456/789"
    )
    body = report.to_github_body()
    assert "#### Brief summary of issue:" in body
    assert "Mapper crashes when adding room to large areas" in body
    assert "#### Steps to reproduce the issue:" in body
    assert "1. Open area with >500 rooms" in body
    assert "#### Error output" in body
    assert "Segfault at 0x7fff5fbff8c0" in body
    assert "Auto-generated from Discord" in body


def test_bug_report_title_truncates() -> None:
    """Title should truncate long summaries to 80 chars."""
    report = BugReport(
        summary="A" * 100, steps=[], error_output="", extra_info="",
        labels=[], source_channel_id="123", source_user_id="456", discord_link=""
    )
    assert len(report.title) <= 80
    assert report.title.endswith("...")


def test_bug_report_no_error_shows_na() -> None:
    """Empty error_output should show N/A in body."""
    report = BugReport(
        summary="Test bug", steps=["Step 1"], error_output="", extra_info="Info",
        labels=[], source_channel_id="123", source_user_id="456", discord_link=""
    )
    body = report.to_github_body()
    assert "N/A" in body


def test_bug_report_from_llm_output() -> None:
    """Should parse structured LLM JSON response into BugReport."""
    llm_output = {
        "summary": "Test summary", "steps": ["Step 1", "Step 2"],
        "error_output": "Error here", "extra_info": "Version 1.0",
        "confidence": "high", "missing_info": None
    }
    report = BugReport.from_llm_output(
        llm_output, source_channel_id="123", source_user_id="456",
        discord_link="https://discord.com/..."
    )
    assert report.summary == "Test summary"
    assert report.steps == ["Step 1", "Step 2"]
    assert report.confidence == "high"
