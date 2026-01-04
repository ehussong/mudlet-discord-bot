"""Bug report data model."""
from dataclasses import dataclass
from typing import Any


@dataclass
class BugReport:
    """Structured bug report extracted from Discord conversation."""

    summary: str
    steps: list[str]
    error_output: str
    extra_info: str
    labels: list[str]
    source_channel_id: str
    source_user_id: str
    discord_link: str
    confidence: str = "high"
    missing_info: str | None = None

    @property
    def title(self) -> str:
        """Generate issue title, truncated to 80 chars."""
        if len(self.summary) <= 80:
            return self.summary
        return self.summary[:77] + "..."

    def to_github_body(self) -> str:
        """Format report as GitHub issue body matching Mudlet template."""
        steps_formatted = "\n".join(
            f"{i}. {step}" for i, step in enumerate(self.steps, 1)
        ) if self.steps else "N/A"
        error = self.error_output.strip() if self.error_output.strip() else "N/A"
        extra = self.extra_info if self.extra_info.strip() else "N/A"

        return f"""#### Brief summary of issue:
{self.summary}

#### Steps to reproduce the issue:
{steps_formatted}

#### Error output
{error}

#### Extra information, such as the Mudlet version, operating system and ideas for how to solve:
{extra}

---
*Auto-generated from Discord by mudlet-bug-bot • [Original conversation]({self.discord_link})*"""

    @classmethod
    def from_llm_output(
        cls,
        llm_output: dict[str, Any],
        source_channel_id: str,
        source_user_id: str,
        discord_link: str,
        labels: list[str] | None = None
    ) -> "BugReport":
        """Create BugReport from parsed LLM JSON response."""
        return cls(
            summary=llm_output.get("summary", ""),
            steps=llm_output.get("steps", []),
            error_output=llm_output.get("error_output", ""),
            extra_info=llm_output.get("extra_info", ""),
            labels=labels or [],
            source_channel_id=source_channel_id,
            source_user_id=source_user_id,
            discord_link=discord_link,
            confidence=llm_output.get("confidence", "high"),
            missing_info=llm_output.get("missing_info")
        )
