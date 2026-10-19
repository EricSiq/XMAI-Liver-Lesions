"""
Comprehensive patient-level evaluation metrics, bootstrap confidence intervals,
Wilson score intervals, and McNemar discordance tests.
Conforms to XMAI Design Document Section 9.
"""

from typing import Any, Callable, Dict, List, Tuple
import numpy as np
from scipy import stats
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)

from xmai.data.schemas import PredictionRow


def compute_patient_metrics(predictions: List[PredictionRow]) -> Dict[str, Any]:
    """Computes patient-level discriminative and probabilistic metrics."""
    y_true = np.array([1 if p.true_label == "HCC" else 0 for p in predictions])
    y_pred = np.array([1 if p.pred_label == "HCC" else 0 for p in predictions])
    y_prob = np.array([p.prob_vector["HCC"] for p in predictions])

    # Class counts
    n_hcc = int(y_true.sum())
    n_hem = int(len(y_true) - n_hcc)

    acc = float(accuracy_score(y_true, y_pred))
    bal_acc = float(balanced_accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    # Specificity = recall of negative class
    spec = float(recall_score(1 - y_true, 1 - y_pred, zero_division=0))

    try:
        auc = float(roc_auc_score(y_true, y_prob))
    except Exception:
        auc = 0.5

    loss = float(log_loss(y_true, np.column_stack([1.0 - y_prob, y_prob]), labels=[0, 1]))
    brier = float(brier_score_loss(y_true, y_prob))

    # Expected Calibration Error (ECE) with 10 bins
    ece = compute_ece(y_true, y_prob, n_bins=10)

    return {
        "n_patients": len(predictions),
        "n_hcc": n_hcc,
        "n_hem": n_hem,
        "accuracy": acc,
        "balanced_accuracy": bal_acc,
        "precision": prec,
        "recall_sensitivity": rec,
        "specificity": spec,
        "f1": f1,
        "auc": auc,
        "log_loss": loss,
        "brier_score": brier,
        "ece": ece,
    }


def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """Computes Expected Calibration Error across n_bins."""
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    n = len(y_true)

    for i in range(n_bins):
        bin_lower, bin_upper = bin_boundaries[i], bin_boundaries[i + 1]
        in_bin = (y_prob > bin_lower) & (y_prob <= bin_upper) if i > 0 else (y_prob >= bin_lower) & (y_prob <= bin_upper)
        bin_size = np.sum(in_bin)

        if bin_size > 0:
            bin_acc = np.mean(y_true[in_bin])
            bin_conf = np.mean(y_prob[in_bin])
            ece += (bin_size / n) * np.abs(bin_acc - bin_conf)

    return float(ece)


def compute_bootstrap_ci(
    predictions: List[PredictionRow],
    metric_key: str = "balanced_accuracy",
    n_bootstraps: int = 1000,
    seed: int = 42,
    alpha: float = 0.05,
) -> Tuple[float, float]:
    """
    Computes patient-level percentile bootstrap confidence intervals.
    Returns (ci_lower, ci_upper).
    """
    if len(predictions) == 0:
        return 0.0, 0.0

    y_true = np.array([1 if p.true_label == "HCC" else 0 for p in predictions])
    y_pred = np.array([1 if p.pred_label == "HCC" else 0 for p in predictions])
    y_prob = np.array([p.prob_vector["HCC"] for p in predictions])

    rng = np.random.RandomState(seed)
    n = len(predictions)
    boot_stats = []

    for _ in range(n_bootstraps):
        idx = rng.choice(n, size=n, replace=True)
        yt, yp, ypr = y_true[idx], y_pred[idx], y_prob[idx]

        if len(np.unique(yt)) < 2:
            continue

        if metric_key == "accuracy":
            val = float(np.mean(yt == yp))
        elif metric_key == "balanced_accuracy":
            sens = np.sum((yt == 1) & (yp == 1)) / max(1, np.sum(yt == 1))
            spec = np.sum((yt == 0) & (yp == 0)) / max(1, np.sum(yt == 0))
            val = float(0.5 * (sens + spec))
        elif metric_key in {"auc", "roc_auc"}:
            val = float(roc_auc_score(yt, ypr))
        else:
            # Fallback for other metrics
            sampled_preds = [predictions[i] for i in idx]
            m = compute_patient_metrics(sampled_preds)
            val = m[metric_key]

        boot_stats.append(val)

    if len(boot_stats) == 0:
        return 0.0, 0.0

    lower_p = 100 * (alpha / 2)
    upper_p = 100 * (1 - alpha / 2)
    return float(np.percentile(boot_stats, lower_p)), float(np.percentile(boot_stats, upper_p))


def compute_wilson_ci(k_success: int, n_total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """
    Computes Wilson score interval for external sensitivity/accuracy on small/asymmetric cohorts.
    Used for Track C TCIA HCC sensitivity (Section 9.4).
    """
    if n_total == 0:
        return 0.0, 0.0
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    p = k_success / n_total
    denom = 1 + z**2 / n_total
    center = (p + z**2 / (2 * n_total)) / denom
    margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n_total)) / n_total) / denom
    return float(max(0.0, center - margin)), float(min(1.0, center + margin))


def compute_mcnemar_test(
    preds_a: List[PredictionRow],
    preds_b: List[PredictionRow],
) -> Dict[str, Any]:
    """
    Performs exact McNemar test between two models on identical patients.
    Counts:
    - b: A correct, B incorrect (rescue by A)
    - c: A incorrect, B correct (harm by A)
    """
    assert len(preds_a) == len(preds_b)
    map_b = {p.patient_id: p for p in preds_b}

    both_correct = 0
    both_wrong = 0
    a_correct_b_wrong = 0
    b_correct_a_wrong = 0

    for pa in preds_a:
        pb = map_b[pa.patient_id]
        corr_a = (pa.pred_label == pa.true_label)
        corr_b = (pb.pred_label == pb.true_label)

        if corr_a and corr_b:
            both_correct += 1
        elif not corr_a and not corr_b:
            both_wrong += 1
        elif corr_a and not corr_b:
            a_correct_b_wrong += 1
        else:
            b_correct_a_wrong += 1

    # Exact binomial p-value on discordant pairs
    b = a_correct_b_wrong
    c = b_correct_a_wrong
    n_discordant = b + c
    p_value = stats.binomtest(b, n_discordant, p=0.5).pvalue if n_discordant > 0 else 1.0

    return {
        "both_correct": both_correct,
        "both_wrong": both_wrong,
        "rescued_by_a": b,
        "rescued_by_b": c,
        "n_discordant": n_discordant,
        "discordant_pairs": n_discordant,
        "net_gain_a": b - c,
        "net_gain_b": c - b,
        "mcnemar_p_value": float(p_value),
    }
