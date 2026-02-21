"""Confidence computation for agent outputs."""

from __future__ import annotations


def compute_confidence(source_ratio: float, consistency: float, verifier_risk: float) -> tuple[float, dict[str, float]]:
    """
    Compute confidence score with breakdown.

    Args:
        source_ratio: Ratio of grounded claims to total claims (0-1)
        consistency: Internal consistency score (0-1)
        verifier_risk: Risk score from verifier (0-1, lower is better)

    Returns:
        Tuple of (overall_confidence, breakdown_dict)
    """
    # Weighted average of components
    weights = {
        "source_quality": 0.4,
        "consistency": 0.35,
        "verifier_pass": 0.25,
    }

    source_score = source_ratio
    verifier_score = 1.0 - verifier_risk

    overall = (
        source_score * weights["source_quality"]
        + consistency * weights["consistency"]
        + verifier_score * weights["verifier_pass"]
    )

    breakdown = {
        "source_quality": source_score,
        "consistency": consistency,
        "verifier_pass": verifier_score,
        "overall": overall,
    }

    return round(overall, 3), breakdown
