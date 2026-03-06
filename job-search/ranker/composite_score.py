"""Composite scoring: combines semantic, skill, title, location, and stack signals."""

import re

from .config import (
    CANDIDATE_SKILL_KEYWORDS,
    COMPOSITE_WEIGHTS,
    TARGET_TITLE_PATTERNS,
    TARGET_LOCATIONS,
)


def _skill_match_score(job: dict) -> float:
    """Fraction of candidate skills found in job text (0.0 - 1.0)."""
    text = (
        (job.get("title") or "") + " " +
        (job.get("description") or "")
    ).lower()
    if not text.strip():
        return 0.0
    matched = sum(1 for kw in CANDIDATE_SKILL_KEYWORDS if kw in text)
    # Normalize: hitting 8+ keywords out of ~35 is a perfect score
    return min(matched / 8.0, 1.0)


def _title_match_score(job: dict) -> float:
    """How well the job title matches target role patterns (0.0 - 1.0)."""
    title = (job.get("title") or "").lower()
    if not title:
        return 0.0
    hits = sum(1 for pat in TARGET_TITLE_PATTERNS if re.search(pat, title))
    # 2+ pattern hits = perfect score
    return min(hits / 2.0, 1.0)


def _location_match_score(job: dict) -> float:
    """Does the job location match target regions (0.0 or 1.0)."""
    location = (job.get("location") or "").lower()
    region = (job.get("region") or "").lower()
    title = (job.get("title") or "").lower()
    combined = f"{location} {region} {title}"
    if not combined.strip():
        return 0.0
    if any(loc in combined for loc in TARGET_LOCATIONS):
        return 1.0
    # Check description for remote mentions
    desc = (job.get("description") or "").lower()
    if "remote" in desc or "télétravail" in desc or "full remote" in desc:
        return 0.8
    return 0.0


def _stack_depth_score(job: dict) -> float:
    """How focused the resume chunk matches are on the same stack (0.0 - 1.0).

    If all top chunks come from the same stack variant, it's a deeper match.
    """
    chunks = job.get("relevant_chunks", [])
    if not chunks:
        return 0.0
    stacks = [c.get("metadata", {}).get("stack", "general") for c in chunks]
    if not stacks:
        return 0.0
    # Count how many chunks match the dominant stack
    dominant = max(set(stacks), key=stacks.count)
    agreement = stacks.count(dominant) / len(stacks)
    # Bonus if matched stack is specific (not "general")
    if dominant != "general":
        return min(agreement * 1.2, 1.0)
    return agreement * 0.7


def compute_composite_score(job: dict) -> dict:
    """Compute a composite score from multiple signals.

    Returns a dict with:
        - composite_score: float (0.0 - 1.0)
        - score_breakdown: dict of individual signal scores
    """
    semantic = job.get("semantic_score", 0.0)

    breakdown = {
        "semantic":       round(semantic, 4),
        "skill_match":    round(_skill_match_score(job), 4),
        "title_match":    round(_title_match_score(job), 4),
        "location_match": round(_location_match_score(job), 4),
        "stack_depth":    round(_stack_depth_score(job), 4),
    }

    composite = sum(
        COMPOSITE_WEIGHTS[signal] * breakdown[signal]
        for signal in COMPOSITE_WEIGHTS
    )

    return {
        "composite_score": round(composite, 4),
        "score_breakdown": breakdown,
    }
