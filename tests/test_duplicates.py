# tests/test_duplicates.py
from unittest.mock import MagicMock

from bot.services.duplicates import DuplicateDetector, extract_keywords


def test_extract_keywords_basic() -> None:
    text = "The mapper crashes when I add a room"
    keywords = extract_keywords(text)
    assert "mapper" in keywords
    assert "room" in keywords
    assert "the" not in keywords  # stop word


def test_extract_keywords_preserves_technical_terms() -> None:
    text = "sendGMCP function throws error in Lua script"
    keywords = extract_keywords(text)
    assert any(k.lower() == "sendgmcp" for k in keywords)
    # Check for lua in some form
    assert any("lua" in k.lower() for k in keywords)


def test_extract_keywords_limits_count() -> None:
    text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10"
    keywords = extract_keywords(text, max_keywords=5)
    assert len(keywords) <= 5


def test_duplicate_detector_find_duplicates() -> None:
    mock_github = MagicMock()
    mock_github.search_issues.return_value = [
        {"number": 123, "title": "Similar bug", "url": "https://...", "state": "open"},
        {"number": 456, "title": "Another bug", "url": "https://...", "state": "closed"},
    ]
    detector = DuplicateDetector(mock_github)
    results = detector.find_duplicates(
        "Mapper crashes when adding room", ["Open mapper", "Add room"]
    )
    assert len(results) == 2
    mock_github.search_issues.assert_called_once()


def test_duplicate_detector_high_confidence() -> None:
    mock_github = MagicMock()
    mock_github.search_issues.return_value = [
        {
            "number": 123,
            "title": "Mapper crashes when adding room",
            "url": "https://...",
            "state": "open",
        },
    ]
    detector = DuplicateDetector(mock_github)
    results = detector.find_duplicates("Mapper crashes when adding a room", [])
    assert results[0]["confidence"] == "high"


def test_duplicate_detector_skips_closed_for_high_confidence() -> None:
    mock_github = MagicMock()
    mock_github.search_issues.return_value = [
        {
            "number": 123,
            "title": "Mapper crashes when adding room",
            "url": "https://...",
            "state": "closed",
        },
    ]
    detector = DuplicateDetector(mock_github)
    results = detector.find_duplicates("Mapper crashes when adding a room", [])
    assert results[0]["confidence"] in ("medium", "low")


def test_has_high_confidence_duplicate() -> None:
    """has_high_confidence_duplicate should return True if high confidence duplicate exists."""
    mock_github = MagicMock()
    mock_github.search_issues.return_value = [
        {
            "number": 123,
            "title": "Mapper crashes when adding room",
            "url": "https://...",
            "state": "open",
        },
    ]
    detector = DuplicateDetector(mock_github)
    assert detector.has_high_confidence_duplicate("Mapper crashes when adding a room", []) is True
