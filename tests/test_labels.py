# tests/test_labels.py
from bot.services.labels import detect_labels


def test_detect_windows() -> None:
    text = "I'm using Mudlet on Windows 11 and the mapper crashes"
    assert "OS:Windows" in detect_labels(text)


def test_detect_macos() -> None:
    text = "Running on macOS Sonoma, getting a freeze"
    assert "OS:macOS" in detect_labels(text)


def test_detect_linux() -> None:
    text = "Ubuntu 22.04, Mudlet 4.18"
    assert "OS:GNU/Linux" in detect_labels(text)


def test_detect_mapper_bug() -> None:
    text = "The mapper room exits are broken"
    assert "mapper bug" in detect_labels(text)


def test_detect_high_severity() -> None:
    text = "App crashes when I click the button"
    assert "high" in detect_labels(text)


def test_detect_regression() -> None:
    text = "This used to work in version 4.17"
    assert "regression" in detect_labels(text)


def test_detect_multiple_labels() -> None:
    text = "Windows 11, mapper crashes when adding room"
    labels = detect_labels(text)
    assert "OS:Windows" in labels
    assert "mapper bug" in labels
    assert "high" in labels


def test_no_labels_from_unrelated_text() -> None:
    text = "Hello, I have a question about the API"
    assert detect_labels(text) == []


def test_case_insensitive() -> None:
    text = "WINDOWS user here, MAPPER is broken"
    labels = detect_labels(text)
    assert "OS:Windows" in labels
    assert "mapper bug" in labels
