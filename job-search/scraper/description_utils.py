"""Utilities for extracting skill-relevant sentences from job descriptions."""

import re
from html import unescape

from ranker.config import CANDIDATE_SKILL_KEYWORDS

# Pre-compile a pattern matching any skill keyword (whole-word, case-insensitive)
_SKILL_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(kw) for kw in CANDIDATE_SKILL_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MULTI_SPACE_RE = re.compile(r"\s+")


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = _HTML_TAG_RE.sub(" ", text)
    text = unescape(text)
    return _MULTI_SPACE_RE.sub(" ", text).strip()


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences (simple heuristic)."""
    # Split on period/exclamation/question followed by space+capital, or newlines
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])|[\n\r]+", text)
    return [s.strip() for s in parts if s.strip()]


def extract_skill_sentences(text: str, max_chars: int = 800) -> str:
    """Strip HTML, split into sentences, keep only those containing skill keywords.

    Returns a string of skill-relevant sentences, truncated to max_chars.
    """
    clean = _strip_html(text)
    if not clean:
        return ""

    sentences = _split_sentences(clean)
    kept = []
    total = 0

    for sentence in sentences:
        if _SKILL_PATTERN.search(sentence):
            if total + len(sentence) + 2 > max_chars:
                break
            kept.append(sentence)
            total += len(sentence) + 2  # account for ". " join

    return ". ".join(kept)


def count_skill_matches(text: str) -> int:
    """Count how many distinct skill keywords appear in text."""
    if not text:
        return 0
    text_lower = text.lower()
    return sum(1 for kw in CANDIDATE_SKILL_KEYWORDS if kw in text_lower)
