# bot/services/labels.py
"""Label auto-detection from bug report text."""

import re

LABEL_PATTERNS: dict[str, str] = {
    # Operating systems
    r"\b(windows|win10|win11|win\s*\d+)\b": "OS:Windows",
    r"\b(macos|mac\s*os|osx|macbook|sonoma|ventura|monterey)\b": "OS:macOS",
    r"\b(linux|ubuntu|debian|fedora|arch|manjaro|mint)\b": "OS:GNU/Linux",
    # Components
    r"\b(map|mapper|room|area|exit|path)\b": "mapper bug",
    r"\b(lua|script|trigger|alias|timer|keybind)\b": "Lua only",
    r"\b(ui|button|toolbar|font|display|window|dialog)\b": "UI",
    r"\b(network|connection|telnet|gmcp|msdp)\b": "networking",
    # Severity
    r"\b(crash(es|ed|ing)?|segfault|freeze[sd]?|hang[s]?|unresponsive)\b": "high",
    r"\b(regression|used\s+to\s+work|worked\s+before|broke|breaking)\b": "regression",
    # Type
    r"\b(feature\s+request|would\s+be\s+nice|wish|suggestion|please\s+add)\b": "wishlist",
    r"\b(documentation|docs|unclear|confusing)\b": "needs documentation",
}

_COMPILED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(pattern, re.IGNORECASE), label) for pattern, label in LABEL_PATTERNS.items()
]


def detect_labels(text: str) -> list[str]:
    """Detect applicable labels from text using regex patterns."""
    detected: set[str] = set()
    for pattern, label in _COMPILED_PATTERNS:
        if pattern.search(text):
            detected.add(label)
    return sorted(detected)


def validate_labels(detected: list[str], valid_labels: list[str]) -> list[str]:
    """Filter detected labels to only those that exist in the repository."""
    valid_set = set(valid_labels)
    return [label for label in detected if label in valid_set]
