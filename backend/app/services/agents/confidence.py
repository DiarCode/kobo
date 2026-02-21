from __future__ import annotations

from math import exp

from app.domain.schemas import ConfidenceBreakdown


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + exp(-value))


def compute_confidence(source_ratio: float, consistency: float, verifier_risk: float) -> tuple[float, ConfidenceBreakdown]:
    raw = (0.40 * source_ratio) + (0.35 * consistency) + (0.25 * (1.0 - verifier_risk))
    calibrated = sigmoid((raw * 4.0) - 2.0)
    breakdown = ConfidenceBreakdown(
        source_ratio=round(source_ratio, 4),
        consistency=round(consistency, 4),
        verifier_risk=round(verifier_risk, 4),
    )
    return round(calibrated, 4), breakdown
