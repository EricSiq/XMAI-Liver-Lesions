"""
Unit tests for Selective Classification and Clinical Uncertainty Referral.
"""

import pytest
from xmai.data.schemas import PredictionRow
from xmai.evaluation.selective_classification import (
    compute_risk_coverage_curve,
    compute_clinical_referral_rate,
    compare_multimodal_referral_efficiency,
)


@pytest.fixture
def mock_predictions():
    # 10 mock patients: 8 high confidence correct, 2 low confidence with errors
    rows = []
    for i in range(8):
        rows.append(PredictionRow(
            patient_id=f"PAT_{i}",
            track="A",
            fold=0,
            seed=42,
            model_id="M1",
            true_label="HCC",
            pred_label="HCC",
            prob_vector={"Hemangioma": 0.05, "HCC": 0.95},
            margin=0.90,
            is_calibrated=True,
            is_error=False,
            is_low_margin=False,
            modality_mask=[1, 0, 1],
        ))
    for i in range(8, 10):
        rows.append(PredictionRow(
            patient_id=f"PAT_{i}",
            track="A",
            fold=0,
            seed=42,
            model_id="M1",
            true_label="Hemangioma",
            pred_label="HCC",
            prob_vector={"Hemangioma": 0.48, "HCC": 0.52},
            margin=0.04,
            is_calibrated=True,
            is_error=True,
            is_low_margin=True,
            modality_mask=[1, 0, 1],
        ))
    return rows


def test_compute_risk_coverage_curve(mock_predictions):
    rc = compute_risk_coverage_curve(mock_predictions, n_thresholds=20)
    assert "coverages" in rc
    assert "risks" in rc
    assert "aurc" in rc
    assert "e_aurc" in rc

    assert len(rc["coverages"]) > 0
    assert 0.0 <= rc["aurc"] <= 1.0
    assert rc["e_aurc"] >= 0.0
    assert rc["full_coverage_error"] == 0.20  # 2 errors out of 10


def test_compute_clinical_referral_rate(mock_predictions):
    # At target_risk=0.0 (zero errors tolerated), the 2 errors with margin=0.04 should be referred
    ref = compute_clinical_referral_rate(mock_predictions, target_risk=0.0)
    assert ref["max_autonomous_coverage"] == pytest.approx(0.80)  # 80% autonomous coverage
    assert ref["required_referral_rate"] == pytest.approx(0.20)   # 20% referral required


def test_compare_multimodal_referral_efficiency(mock_predictions):
    preds_dict = {
        "A1": mock_predictions,
        "A4": mock_predictions,
    }
    df = compare_multimodal_referral_efficiency(preds_dict, target_risk=0.01)
    assert len(df) == 2
    assert "Autonomous Coverage (%)" in df.columns
    assert "Referral Rate (%)" in df.columns
    assert "AURC (x10^-3)" in df.columns


@pytest.mark.parametrize("budget", [0.0005, 0.001, 0.005, 0.01, 0.05])
def test_monotonic_coverage_with_risk_budget(mock_predictions, budget):
    """Higher clinical risk tolerance must monotonically permit greater or equal autonomous coverage."""
    ref_strict = compute_clinical_referral_rate(mock_predictions, target_risk=0.0)
    ref_budget = compute_clinical_referral_rate(mock_predictions, target_risk=budget)
    assert ref_budget["max_autonomous_coverage"] >= ref_strict["max_autonomous_coverage"] - 1e-6


def test_perfect_model_bounds():
    """An ideal model with 0 errors must yield AURC == 0, E-AURC == 0, and 100% autonomous coverage."""
    perfect_preds = [
        PredictionRow(
            patient_id=f"PERFECT_{i}",
            track="A", fold=0, seed=42, model_id="Ideal",
            true_label="HCC", pred_label="HCC",
            prob_vector={"Hemangioma": 0.01, "HCC": 0.99},
            margin=0.98, is_calibrated=True, is_error=False,
            is_low_margin=False, modality_mask=[1, 0, 1]
        )
        for i in range(20)
    ]
    rc = compute_risk_coverage_curve(perfect_preds, n_thresholds=20)
    assert rc["aurc"] == pytest.approx(0.0, abs=1e-5)
    assert rc["e_aurc"] == pytest.approx(0.0, abs=1e-5)

    ref = compute_clinical_referral_rate(perfect_preds, target_risk=0.001)
    assert ref["max_autonomous_coverage"] == pytest.approx(1.0)
    assert ref["required_referral_rate"] == pytest.approx(0.0)


def test_completely_failing_model_bounds():
    """A completely incorrect model (100% error rate) must require 100% referral at strict risk budgets."""
    failing_preds = [
        PredictionRow(
            patient_id=f"FAIL_{i}",
            track="A", fold=0, seed=42, model_id="Broken",
            true_label="HCC", pred_label="Hemangioma",
            prob_vector={"Hemangioma": 0.80, "HCC": 0.20},
            margin=0.60, is_calibrated=True, is_error=True,
            is_low_margin=False, modality_mask=[1, 0, 1]
        )
        for i in range(20)
    ]
    ref = compute_clinical_referral_rate(failing_preds, target_risk=0.01)
    assert ref["max_autonomous_coverage"] == pytest.approx(0.0)
    assert ref["required_referral_rate"] == pytest.approx(1.0)

