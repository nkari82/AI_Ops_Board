from __future__ import annotations

from backend.services.recommendation_quality import (
    apply_sparse_data_score_guard,
    cap_combo_boost,
    compute_quality_confidence,
    quality_band_from_confidence,
)


def test_compute_quality_confidence_increases_with_evidence_and_feedback() -> None:
    low = compute_quality_confidence(0, 0)
    mid = compute_quality_confidence(3, 1)
    high = compute_quality_confidence(10, 6)

    assert low == 0.0
    assert mid > low
    assert high > mid
    assert high <= 1.0


def test_quality_band_thresholds() -> None:
    assert quality_band_from_confidence(0.1) == "low"
    assert quality_band_from_confidence(0.4) == "medium"
    assert quality_band_from_confidence(0.8) == "high"


def test_sparse_data_score_guard_penalizes_thin_evidence() -> None:
    assert apply_sparse_data_score_guard(70, 0) == 64
    assert apply_sparse_data_score_guard(70, 2) == 64
    assert apply_sparse_data_score_guard(70, 5) == 68
    assert apply_sparse_data_score_guard(70, 10) == 70


def test_combo_boost_is_capped_for_sparse_domains() -> None:
    assert cap_combo_boost(8, 0) == 0
    assert cap_combo_boost(8, 2) == 2
    assert cap_combo_boost(8, 3) == 8
    assert cap_combo_boost(12, 30) == 8
