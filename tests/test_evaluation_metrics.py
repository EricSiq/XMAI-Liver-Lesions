"""
Unit tests for evaluation metrics, Wilson intervals, bootstrapping, and McNemar test.
"""

import pytest
from xmai.data.schemas import PredictionRow
from xmai.evaluation.metrics import (
    compute_bootstrap_ci,
    compute_mcnemar_test,
    compute_patient_metrics,
    compute_wilson_ci,
)


@pytest.fixture
def mock_predictions():
    preds = []
    # 5 HCC correctly predicted
    for i in range(5):
        preds.append(PredictionRow(
            patient_id=f"HCC_{i}",
            track="A", fold=0, seed=42, model_id="A4",
            true_label="HCC", pred_label="HCC",
            prob_vector={"Hemangioma": 0.2, "HCC": 0.8},
            margin=0.6, is_calibrated=True, is_low_margin=False, is_error=False,
            modality_mask=[1, 0, 1]
        ))
    # 1 HCC mispredicted as Hemangioma
    preds.append(PredictionRow(
        patient_id="HCC_error",
        track="A", fold=0, seed=42, model_id="A4",
        true_label="HCC", pred_label="Hemangioma",
        prob_vector={"Hemangioma": 0.55, "HCC": 0.45},
        margin=0.1, is_calibrated=True, is_low_margin=True, is_error=True,
        modality_mask=[1, 0, 1]
    ))
    # 4 Hemangioma correctly predicted
    for i in range(4):
        preds.append(PredictionRow(
            patient_id=f"Hem_{i}",
            track="A", fold=0, seed=42, model_id="A4",
            true_label="Hemangioma", pred_label="Hemangioma",
            prob_vector={"Hemangioma": 0.85, "HCC": 0.15},
            margin=0.7, is_calibrated=True, is_low_margin=False, is_error=False,
            modality_mask=[1, 0, 1]
        ))
    return preds


def test_patient_metrics_calculation(mock_predictions):
    m = compute_patient_metrics(mock_predictions)
    assert m["n_patients"] == 10
    assert m["n_hcc"] == 6
    assert m["n_hem"] == 4
    # 9 out of 10 correct
    assert m["accuracy"] == pytest.approx(0.9)
    # Sensitivity (HCC recall): 5 / 6 = 0.8333
    assert m["recall_sensitivity"] == pytest.approx(5 / 6)
    # Specificity (Hemangioma recall): 4 / 4 = 1.0
    assert m["specificity"] == pytest.approx(1.0)
    assert m["log_loss"] > 0.0
    assert 0.0 <= m["ece"] <= 1.0


def test_wilson_ci():
    low, high = compute_wilson_ci(90, 100, confidence=0.95)
    assert 0.82 < low < 0.90
    assert 0.90 < high < 0.96

    # Edge cases
    low0, high0 = compute_wilson_ci(0, 10)
    assert low0 == 0.0
    assert high0 > 0.0

    low_full, high_full = compute_wilson_ci(10, 10)
    assert low_full < 1.0
    assert high_full == pytest.approx(1.0)


def test_bootstrap_ci(mock_predictions):
    low, high = compute_bootstrap_ci(mock_predictions, metric_key="accuracy", n_bootstraps=200, seed=42)
    assert 0.5 <= low <= high <= 1.0


def test_mcnemar_discordance(mock_predictions):
    # Create model B where HCC_error is rescued (correct) and Hem_0 is harmed (incorrect)
    preds_b = []
    for p in mock_predictions:
        d = p.model_dump()
        if p.patient_id == "HCC_error":
            d["pred_label"] = "HCC"  # Rescued
        if p.patient_id == "Hem_0":
            d["pred_label"] = "HCC"  # Harmed
        preds_b.append(PredictionRow(**d))

    res = compute_mcnemar_test(mock_predictions, preds_b)
    assert res["both_correct"] == 8
    assert res["both_wrong"] == 0
    assert res["rescued_by_a"] == 1
    assert res["rescued_by_b"] == 1
    assert res["net_gain_a"] == 0
    assert res["mcnemar_p_value"] == 1.0


def test_evaluation_visualizations(mock_predictions, tmp_path):
    from xmai.evaluation.visualization import (
        plot_multimodel_roc_curves,
        plot_reliability_diagrams,
        plot_hypothesis_h1_breakdown,
    )
    preds_dict = {"Model_A": mock_predictions, "Model_B": mock_predictions}

    roc_file = tmp_path / "roc.png"
    plot_multimodel_roc_curves(preds_dict, roc_file)
    assert roc_file.exists() and roc_file.stat().st_size > 0

    rel_file = tmp_path / "rel.png"
    plot_reliability_diagrams(preds_dict, rel_file)
    assert rel_file.exists() and rel_file.stat().st_size > 0

    h1_dummy = {
        "low_margin_rescues": 2,
        "low_margin_harms": 1,
        "low_margin_net_gain": 1,
        "high_margin_rescues": 0,
        "high_margin_harms": 2,
        "high_margin_net_gain": -2,
    }
    h1_file = tmp_path / "h1.png"
    plot_hypothesis_h1_breakdown(h1_dummy, h1_file)
    assert h1_file.exists() and h1_file.stat().st_size > 0


def test_scientific_manuscript_generation(mock_predictions, tmp_path):
    from scripts.generate_scientific_manuscript_artifacts import (
        generate_ablation_tables,
        generate_calibration_ablation_table,
        generate_pairwise_statistical_comparison,
    )
    preds_dict = {
        "A1": mock_predictions,
        "A2": mock_predictions,
        "A3": mock_predictions,
        "A4": mock_predictions,
        "A5": mock_predictions,
        "A6": mock_predictions,
        "A7": mock_predictions,
        "A8": mock_predictions,
        "A9": mock_predictions,
    }

    md_tab, tex_tab = generate_ablation_tables(preds_dict, tmp_path, n_bootstraps=20)
    assert "A1: B-mode Only" in md_tab
    assert "A8: Cross-Modal Attention" in md_tab
    assert "\\begin{table*}" in tex_tab
    assert (tmp_path / "ablation_table.md").exists()
    assert (tmp_path / "ablation_table.tex").exists()

    cal_tab = generate_calibration_ablation_table(preds_dict, tmp_path)
    assert "Uncal ECE" in cal_tab
    assert (tmp_path / "calibration_ablation.md").exists()

    pair_tab = generate_pairwise_statistical_comparison(preds_dict, tmp_path, n_bootstraps=20)
    assert "Pairwise Statistical Significance" in pair_tab
    assert (tmp_path / "pairwise_statistical_comparison.md").exists()

    from scripts.generate_scientific_manuscript_artifacts import generate_selective_classification_table
    sel_md, sel_tex = generate_selective_classification_table(preds_dict, tmp_path, target_risk=0.01)
    assert "Autonomous Coverage (%)" in sel_md
    assert (tmp_path / "selective_classification.md").exists()


