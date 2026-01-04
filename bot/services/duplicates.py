# bot/services/duplicates.py
"""Duplicate detection service for finding similar issues."""

import re
from difflib import SequenceMatcher
from typing import TypedDict

from bot.services.github_client import GitHubClient

# Common words to filter from keyword extraction
STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "dare",
    "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
    "from", "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "under", "again", "further", "then", "once", "here",
    "there", "when", "where", "why", "how", "all", "each", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "just", "also", "now", "and",
    "but", "or", "if", "because", "until", "while", "although", "though",
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you",
    "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself",
    "she", "her", "hers", "herself", "it", "its", "itself", "they", "them",
    "their", "theirs", "themselves", "what", "which", "who", "whom", "this",
    "that", "these", "those", "am", "isn", "aren", "wasn", "weren", "hasn",
    "haven", "hadn", "doesn", "don", "didn", "won", "wouldn", "couldn",
    "shouldn", "mustn", "let", "s", "t", "ve", "ll", "d", "re", "m",
})


class DuplicateResult(TypedDict):
    """Result from duplicate detection."""

    number: int
    title: str
    url: str
    state: str
    confidence: str


def extract_keywords(text: str, max_keywords: int = 10) -> list[str]:
    """
    Extract meaningful keywords from text, filtering stop words.

    Args:
        text: The text to extract keywords from
        max_keywords: Maximum number of keywords to return

    Returns:
        List of lowercase keywords
    """
    # Extract words using regex (alphanumeric sequences)
    words = re.findall(r"[a-zA-Z0-9]+", text)

    # Filter stop words and short words, convert to lowercase
    keywords = [
        word.lower()
        for word in words
        if word.lower() not in STOP_WORDS and len(word) > 1
    ]

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique_keywords: list[str] = []
    for keyword in keywords:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)

    return unique_keywords[:max_keywords]


def similarity_score(s1: str, s2: str) -> float:
    """
    Calculate similarity score between two strings using SequenceMatcher.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Similarity score between 0.0 and 1.0
    """
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()


class DuplicateDetector:
    """Detects potential duplicate issues using GitHub search and string similarity."""

    def __init__(self, github_client: GitHubClient) -> None:
        """
        Initialize the duplicate detector.

        Args:
            github_client: GitHubClient instance for searching issues
        """
        self._github = github_client

    def find_duplicates(
        self,
        title: str,
        steps: list[str],
        max_results: int = 5,
    ) -> list[DuplicateResult]:
        """
        Find potential duplicate issues based on title and steps.

        Args:
            title: The title of the new issue
            steps: List of reproduction steps
            max_results: Maximum number of results to return

        Returns:
            List of potential duplicates with confidence scores
        """
        # Extract keywords from title and steps
        title_keywords = extract_keywords(title)
        step_text = " ".join(steps)
        step_keywords = extract_keywords(step_text)

        # Combine keywords, prioritizing title keywords
        all_keywords = title_keywords + [k for k in step_keywords if k not in title_keywords]
        search_keywords = all_keywords[:5]  # Limit to 5 for search

        if not search_keywords:
            return []

        # Search GitHub for matching issues
        search_results = self._github.search_issues(search_keywords, max_results=max_results)

        # Add confidence scores
        results: list[DuplicateResult] = []
        for issue in search_results:
            issue_title = issue["title"]
            score = similarity_score(title, issue_title)

            # Determine confidence level
            # High confidence: similarity > 0.7 AND state == "open"
            if score > 0.7 and issue["state"] == "open":
                confidence = "high"
            elif score > 0.5:
                confidence = "medium"
            else:
                confidence = "low"

            results.append(
                DuplicateResult(
                    number=issue["number"],
                    title=issue_title,
                    url=issue["url"],
                    state=issue["state"],
                    confidence=confidence,
                )
            )

        return results

    def has_high_confidence_duplicate(
        self,
        title: str,
        steps: list[str],
    ) -> bool:
        """
        Check if there's a high confidence duplicate for the given issue.

        Args:
            title: The title of the new issue
            steps: List of reproduction steps

        Returns:
            True if a high confidence duplicate exists
        """
        duplicates = self.find_duplicates(title, steps)
        return any(d["confidence"] == "high" for d in duplicates)
