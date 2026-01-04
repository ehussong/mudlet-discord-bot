# tests/test_config.py
import os
from unittest.mock import patch


def test_config_loads_discord_token() -> None:
    """Config should load DISCORD_BOT_TOKEN from environment."""
    with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "test-token-123"}):
        import importlib

        import bot.config
        importlib.reload(bot.config)
        config = bot.config.Config()
        assert config.discord_token == "test-token-123"


def test_config_parses_allowed_roles() -> None:
    """Config should parse comma-separated roles into list."""
    env = {
        "DISCORD_BOT_TOKEN": "token",
        "BUG_COMMAND_ROLES": "Developer,Moderator,Bug Triager"
    }
    with patch.dict(os.environ, env, clear=False):
        import importlib

        from bot import config
        importlib.reload(config)
        cfg = config.Config()
        assert cfg.allowed_roles == ["Developer", "Moderator", "Bug Triager"]


def test_config_empty_roles_returns_empty_list() -> None:
    """Empty BUG_COMMAND_ROLES should return empty list."""
    env = {"DISCORD_BOT_TOKEN": "token", "BUG_COMMAND_ROLES": ""}
    with patch.dict(os.environ, env, clear=False):
        import importlib

        from bot import config
        importlib.reload(config)
        cfg = config.Config()
        assert cfg.allowed_roles == []
