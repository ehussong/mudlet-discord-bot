"""Configuration management for the Mudlet Bug Bot."""
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """Bot configuration loaded from environment variables."""

    # Discord
    discord_token: str = field(default_factory=lambda: os.getenv("DISCORD_BOT_TOKEN", ""))
    test_guild_id: str | None = field(
        default_factory=lambda: os.getenv("DISCORD_TEST_GUILD_ID") or None
    )

    # LLM
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai"))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))

    # GitHub
    github_app_id: str = field(default_factory=lambda: os.getenv("GITHUB_APP_ID", ""))
    github_private_key_path: str = field(
        default_factory=lambda: os.getenv("GITHUB_PRIVATE_KEY_PATH", "")
    )
    github_installation_id: str = field(
        default_factory=lambda: os.getenv("GITHUB_INSTALLATION_ID", "")
    )
    github_token: str = field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))
    github_repo: str = field(default_factory=lambda: os.getenv("GITHUB_REPO", "Mudlet/Mudlet"))

    # Permissions
    allowed_roles: list[str] = field(default_factory=list)

    # Features
    enable_duplicate_detection: bool = field(
        default_factory=lambda: os.getenv("ENABLE_DUPLICATE_DETECTION", "true").lower() == "true"
    )
    enable_image_analysis: bool = field(
        default_factory=lambda: os.getenv("ENABLE_IMAGE_ANALYSIS", "true").lower() == "true"
    )

    # Health check
    health_port: int = field(default_factory=lambda: int(os.getenv("HEALTH_PORT", "8080")))

    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    def __post_init__(self) -> None:
        """Parse complex config values after initialization."""
        roles_str = os.getenv("BUG_COMMAND_ROLES", "")
        self.allowed_roles = [r.strip() for r in roles_str.split(",") if r.strip()]

    def validate(self) -> list[str]:
        """Validate required configuration. Returns list of errors."""
        errors = []
        if not self.discord_token:
            errors.append("DISCORD_BOT_TOKEN is required")
        if not self.openai_api_key and not self.anthropic_api_key:
            errors.append("At least one of OPENAI_API_KEY or ANTHROPIC_API_KEY is required")
        if not self.github_token and not self.github_app_id:
            errors.append("Either GITHUB_TOKEN or GITHUB_APP_ID is required")
        return errors
