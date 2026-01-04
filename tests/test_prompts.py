# tests/test_prompts.py
from config.prompts import EXTRACTION_SYSTEM_PROMPT, format_conversation_prompt


def test_system_prompt_exists() -> None:
    """System prompt should be defined and non-empty."""
    assert EXTRACTION_SYSTEM_PROMPT
    assert len(EXTRACTION_SYSTEM_PROMPT) > 100


def test_system_prompt_mentions_json() -> None:
    """System prompt should instruct JSON output."""
    assert "json" in EXTRACTION_SYSTEM_PROMPT.lower()


def test_system_prompt_mentions_required_fields() -> None:
    """System prompt should mention all required output fields."""
    prompt = EXTRACTION_SYSTEM_PROMPT.lower()
    assert "summary" in prompt
    assert "steps" in prompt
    assert "error" in prompt


def test_format_conversation_prompt() -> None:
    """Should format messages into conversation prompt."""
    messages = [
        {"author": "User1", "content": "The mapper is broken"},
        {"author": "User2", "content": "What version?"},
        {"author": "User1", "content": "4.18.0 on Windows"},
    ]
    prompt = format_conversation_prompt(messages)
    assert "User1: The mapper is broken" in prompt
    assert "User2: What version?" in prompt
    assert "4.18.0 on Windows" in prompt
