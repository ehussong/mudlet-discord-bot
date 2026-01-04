# tests/test_integration.py
"""Integration tests using sample conversation fixtures."""

import json
from pathlib import Path
from typing import Any, cast

import pytest

from bot.services.labels import detect_labels


@pytest.fixture
def sample_conversations() -> dict[str, Any]:
    """Load sample conversations from JSON fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_conversations.json"
    with open(fixture_path) as f:
        return cast(dict[str, Any], json.load(f))


def _get_combined_text(conversation: dict[str, Any]) -> str:
    """Combine all message content from a conversation into a single string."""
    return " ".join(msg["content"] for msg in conversation["messages"])


def test_label_detection_clear_mapper_bug(sample_conversations: dict[str, Any]) -> None:
    """Test label detection for a clear mapper crash on Windows."""
    conversation = sample_conversations["clear_mapper_bug"]
    text = _get_combined_text(conversation)
    detected = detect_labels(text)

    expected = conversation["expected_labels"]
    for label in expected:
        assert label in detected, f"Expected label '{label}' not detected in: {detected}"


def test_label_detection_lua_error(sample_conversations: dict[str, Any]) -> None:
    """Test label detection for Lua scripting error with regression."""
    conversation = sample_conversations["lua_scripting_error"]
    text = _get_combined_text(conversation)
    detected = detect_labels(text)

    expected = conversation["expected_labels"]
    for label in expected:
        assert label in detected, f"Expected label '{label}' not detected in: {detected}"


def test_label_detection_vague_report(sample_conversations: dict[str, Any]) -> None:
    """Test label detection for vague report returns no labels."""
    conversation = sample_conversations["vague_report"]
    text = _get_combined_text(conversation)
    detected = detect_labels(text)

    expected = conversation["expected_labels"]
    assert detected == expected, f"Expected no labels, but got: {detected}"


def test_label_detection_feature_request(sample_conversations: dict[str, Any]) -> None:
    """Test label detection for a feature request."""
    conversation = sample_conversations["feature_request"]
    text = _get_combined_text(conversation)
    detected = detect_labels(text)

    expected = conversation["expected_labels"]
    for label in expected:
        assert label in detected, f"Expected label '{label}' not detected in: {detected}"


def test_label_detection_multi_platform(sample_conversations: dict[str, Any]) -> None:
    """Test label detection for bug reported on multiple platforms."""
    conversation = sample_conversations["multi_platform"]
    text = _get_combined_text(conversation)
    detected = detect_labels(text)

    expected = conversation["expected_labels"]
    for label in expected:
        assert label in detected, f"Expected label '{label}' not detected in: {detected}"
