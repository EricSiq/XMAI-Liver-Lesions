"""
Unit tests for the 5-class / 6-class evaluation metrics suite:
- Multiclass Confusion Matrix
- ECE calibration calculation
- Malignant under-call rate
- Per-class sensitivity, specificity, and F1
- 95% Bootstrap confidence intervals
"""

import pytest
import numpy as np
from xmai.evaluation.multiclass_metrics import (
    compute_multiclass_confusion_matrix,
    compute_multiclass_ece,
    compute_malignant_undercall_rate,
    compute_per_class_metrics,
    compute_multiclass_evaluation_suite,
)
from xmai.data.schemas import TAXONOMY_5CLASS


def test_confusion_matrix_and_per_class_metrics():
    """Verify confusion matrix diagonal and per-class calculations."""
    # 5 classes: 0:HCC, 1:Hem, 2:FNH, 3:Adenoma, 4:ICC
    y_true = np.array([0, 0, 1, 1, 2, 2, 3, 3, 4, 4])
    y_pred = np.array([0, 0, 1, 2, 2, 2, 3, 3, 4, 0])  # One Hem misclassified as FNH, one ICC as HCC

    cm = compute_multiclass_confusion_matrix(y_true, y_pred, num_classes=5)
    assert cm.shape == (5, 5)
    assert cm[0, 0] == 2  # Both HCC correct
    assert cm[1, 2] == 1  # 1 Hem misclassified as FNH

    metrics = compute_per_class_metrics(cm, TAXONOMY_5CLASS)
    assert metrics["HCC"]["sensitivity"] == 1.0
    assert metrics["Hemangioma"]["sensitivity"] == 0.5  # 1/2 correct
    assert metrics["FNH"]["precision"] < 1.0           # FP from Hemangioma


def test_malignant_undercall_rate_detection():
    """Verify calculation of critical malignant under-call safety metric."""
    # Malignant: 0 (HCC), 4 (ICC). Benign: 1 (Hem), 2 (FNH), 3 (Adenoma)
    y_true = np.array([0, 0, 4, 4, 1, 1])
    # Case 0: correctly HCC (0)
    # Case 1: FALSE BENIGN: HCC misclassified as Hem (1) -> undercall!
    # Case 2: correctly ICC (4)
    # Case 3: FALSE BENIGN: ICC misclassified as Adenoma (3) -> undercall!
    # Case 4, 5: Benigns
    y_pred = np.array([0, 1, 4, 3, 1, 1])

    res = compute_malignant_undercall_rate(y_true, y_pred, TAXONOMY_5CLASS)
    assert res["total_malignancies"] == 4
    assert res["undercall_count"] == 2
    assert res["undercall_rate"] == 0.50


def test_multiclass_ece_calibration():
    """Verify Expected Calibration Error calculation on calibrated vs uncalibrated predictions."""
    y_true = np.array([0, 1, 2, 3, 4])

    # Perfect confidence and accuracy
    probs_perfect = np.zeros((5, 5))
    for i in range(5):
        probs_perfect[i, i] = 1.0
    ece_perfect = compute_multiclass_ece(y_true, probs_perfect)
    assert ece_perfect == pytest.approx(0.0, abs=1e-5)

    # Completely overconfident wrong predictions
    probs_wrong = np.zeros((5, 5))
    for i in range(5):
        probs_wrong[i, (i + 1) % 5] = 1.0  # 100% confidence, 0% accuracy
    ece_wrong = compute_multiclass_ece(y_true, probs_wrong)
    assert ece_wrong > 0.80


def test_multiclass_evaluation_suite_complete_report():
    """Verify full evaluation report structure and bootstrap CI validity."""
    np.random.seed(42)
    N = 100
    y_true = np.random.randint(0, 5, size=N)
    # Generate noisy predicted probabilities
    logits = np.random.randn(N, 5)
    for i in range(N):
        logits[i, y_true[i]] += 2.0  # boost true class
    exp_logits = np.exp(logits)
    probs = exp_logits / np.sum(exp_logits, axis=-1, keepdims=True)

    report = compute_multiclass_evaluation_suite(
        y_true=y_true,
        probs=probs,
        class_names=TAXONOMY_5CLASS,
        n_bootstrap=200,
    )

    assert report["num_patients"] == N
    assert report["num_classes"] == 5
    assert 0.0 <= report["macro_f1"] <= 1.0
    assert 0.0 <= report["balanced_accuracy"] <= 1.0
    assert report["macro_f1_ci95"][0] <= report["macro_f1_ci95"][1]
    assert report["balanced_accuracy_ci95"][0] <= report["balanced_accuracy_ci95"][1]
    assert len(report["per_class_metrics"]) == 5
    assert "malignant_undercall_rate" in report
