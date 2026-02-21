from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


@dataclass(slots=True)
class AutonomyComputation:
    score: float
    lower_bound95: float
    tier: str


def wilson_lower_bound(successes: int, total: int, z: float = 1.96) -> float:
    if total == 0:
        return 0.0
    phat = successes / total
    denominator = 1 + (z * z / total)
    center = phat + (z * z) / (2 * total)
    margin = z * sqrt((phat * (1 - phat) + (z * z) / (4 * total)) / total)
    return (center - margin) / denominator


def autonomy_tier(score: float) -> str:
    if score < 0.30:
        return "tier0"
    if score < 0.60:
        return "tier1"
    if score < 0.80:
        return "tier2"
    return "tier3"


def compute_autonomy(successes: int, total: int) -> AutonomyComputation:
    score = (successes / total) if total else 0.0
    lower = wilson_lower_bound(successes, total)
    tier = autonomy_tier(score)
    return AutonomyComputation(score=round(score, 4), lower_bound95=round(lower, 4), tier=tier)
