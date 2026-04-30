from __future__ import annotations


def compute_quality_confidence(evidence_count: int, feedback_count: int) -> float:
    """Return confidence in [0.0, 1.0] based on evidence/feedback volume."""
    evidence = max(0, int(evidence_count))
    feedback = max(0, int(feedback_count))
    confidence = evidence * 0.08 + feedback * 0.05
    return max(0.0, min(1.0, round(confidence, 3)))


def quality_band_from_confidence(confidence: float) -> str:
    value = max(0.0, min(1.0, float(confidence)))
    if value >= 0.7:
        return "high"
    if value >= 0.35:
        return "medium"
    return "low"


def apply_sparse_data_score_guard(score: int, evidence_count: int) -> int:
    base = max(0, min(100, int(score)))
    evidence = max(0, int(evidence_count))
    if evidence < 3:
        return max(0, base - 6)
    if evidence < 8:
        return max(0, base - 2)
    return base


def cap_combo_boost(boost: int, evidence_count: int) -> int:
    requested = max(0, int(boost))
    evidence = max(0, int(evidence_count))
    if evidence == 0:
        return 0
    if evidence < 3:
        return min(requested, 2)
    return min(requested, 8)
