"""
Comprehensive Multiclass Evaluation Suite for 5-Class / 6-Class Focal Liver Lesion AI.
Conforms to CLAIM 2020 and STARD-AI guidelines.
Calculates:
- Multiclass Confusion Matrix
- Per-Class Sensitivity, Specificity, Precision, F1-Score
- Macro-Averaged F1, Balanced Accuracy, Top-2 Accuracy
- Malignant Under-Call Rate (Critical Oncology Safety Metric)
- Multiclass Expected Calibration Error (ECE)
- 95% Bootstrap Confidence Intervals
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from sklearn.metrics import confusion_matrix, f1_score, balanced_accuracy_score

from xmai.data.schemas import TAXONOMY_5CLASS, CLASS_TIER_MAPPING


def compute_multiclass_confusion_matrix(
    y_true: Union[List[int], np.ndarray],
    y_pred: Union[List[int], np.ndarray],
    num_classes: int = 5,
) -> np.ndarray:
    """Computes KxK confusion matrix."""
    return confusion_matrix(y_true, y_pred, labels=list(range(num_classes)))


def compute_multiclass_ece(
    y_true: np.ndarray,
    probs: np.ndarray,
    n_bins: int = 10,
) -> float:
    """
    Computes Multiclass Expected Calibration Error (ECE).
    Evaluates alignment between confidence max_k p_k and empirical correctness.
    """
    if len(y_true) == 0:
        return 0.0

    confidences = np.max(probs, axis=-1)
    predictions = np.argmax(probs, axis=-1)
    accuracies = (predictions == y_true).astype(float)

    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    N = len(y_true)

    for i in range(n_bins):
        in_bin = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
        prop_in_bin = np.mean(in_bin)
        if prop_in_bin > 0:
            avg_accuracy_in_bin = np.mean(accuracies[in_bin])
            avg_confidence_in_bin = np.mean(confidences[in_bin])
            ece += np.abs(avg_accuracy_in_bin - avg_confidence_in_bin) * prop_in_bin

    return float(ece)


def compute_malignant_undercall_rate(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: List[str],
) -> Dict[str, Union[float, int]]:
    """
    Critical Oncology Safety Metric:
    Calculates fraction of true malignant lesions falsely classified as benign.
    """
    mal_classes = {i for i, c in enumerate(class_names) if CLASS_TIER_MAPPING.get(c) == "Malignant"}
    ben_classes = {i for i, c in enumerate(class_names) if CLASS_TIER_MAPPING.get(c) == "Benign"}

    true_mal_mask = np.isin(y_true, list(mal_classes))
    total_malignancies = int(np.sum(true_mal_mask))

    if total_malignancies == 0:
        return {"undercall_rate": 0.0, "undercall_count": 0, "total_malignancies": 0}

    predicted_ben_mask = np.isin(y_pred[true_mal_mask], list(ben_classes))
    undercall_count = int(np.sum(predicted_ben_mask))
    undercall_rate = float(undercall_count / total_malignancies)

    return {
        "undercall_rate": undercall_rate,
        "undercall_count": undercall_count,
        "total_malignancies": total_malignancies,
    }


def compute_per_class_metrics(
    cm: np.ndarray,
    class_names: List[str],
) -> Dict[str, Dict[str, float]]:
    """Computes Sensitivity, Specificity, Precision, and F1 for each lesion category."""
    per_class = {}
    K = cm.shape[0]
    total_samples = np.sum(cm)

    for i, name in enumerate(class_names):
        TP = cm[i, i]
        FN = np.sum(cm[i, :]) - TP
        FP = np.sum(cm[:, i]) - TP
        TN = total_samples - (TP + FN + FP)

        sens = float(TP / (TP + FN)) if (TP + FN) > 0 else 0.0
        spec = float(TN / (TN + FP)) if (TN + FP) > 0 else 0.0
        prec = float(TP / (TP + FP)) if (TP + FP) > 0 else 0.0
        f1 = float(2 * prec * sens / (prec + sens)) if (prec + sens) > 0 else 0.0

        per_class[name] = {
            "sensitivity": round(sens, 4),
            "specificity": round(spec, 4),
            "precision": round(prec, 4),
            "f1_score": round(f1, 4),
            "support": int(TP + FN),
        }

    return per_class


def compute_multiclass_evaluation_suite(
    y_true: Union[List[int], np.ndarray],
    probs: Union[List[List[float]], np.ndarray],
    class_names: Optional[List[str]] = None,
    n_bootstrap: int = 1000,
    random_seed: int = 42,
) -> Dict[str, Any]:
    """
    Computes complete CLAIM-compliant 5-class evaluation report.
    """
    if class_names is None:
        class_names = list(TAXONOMY_5CLASS)

    y_true_arr = np.asarray(y_true, dtype=int)
    probs_arr = np.asarray(probs, dtype=float)
    N = len(y_true_arr)
    if N == 0:
        raise ValueError("Cannot evaluate multiclass metrics on empty patient cohort.")
    if probs_arr.ndim != 2:
        raise ValueError(f"Expected 2D probability matrix [N, K], got shape {probs_arr.shape}")
    if probs_arr.shape[1] != len(class_names):
        raise ValueError(f"Number of classes in probs ({probs_arr.shape[1]}) does not match class_names ({len(class_names)})")

    y_pred_arr = np.argmax(probs_arr, axis=-1)
    K = len(class_names)

    # 1. Core global metrics
    macro_f1 = float(f1_score(y_true_arr, y_pred_arr, average="macro"))
    bal_acc = float(balanced_accuracy_score(y_true_arr, y_pred_arr))
    acc = float(np.mean(y_true_arr == y_pred_arr))

    # Top-2 accuracy
    sorted_preds = np.argsort(-probs_arr, axis=-1)
    top2_correct = np.any(sorted_preds[:, :2] == y_true_arr[:, None], axis=-1)
    top2_acc = float(np.mean(top2_correct))

    # 2. Confusion matrix & per-class breakdown
    cm = compute_multiclass_confusion_matrix(y_true_arr, y_pred_arr, num_classes=K)
    per_class = compute_per_class_metrics(cm, class_names)

    # 3. Calibration ECE
    ece = compute_multiclass_ece(y_true_arr, probs_arr)

    # 4. Oncology Safety: Malignant Under-Call Rate
    undercall_info = compute_malignant_undercall_rate(y_true_arr, y_pred_arr, class_names)

    # 5. Bootstrap Confidence Intervals (95% CI)
    rng = np.random.RandomState(random_seed)
    N = len(y_true_arr)
    bs_macro_f1 = []
    bs_bal_acc = []

    for _ in range(n_bootstrap):
        idx = rng.randint(0, N, size=N)
        b_true = y_true_arr[idx]
        b_pred = y_pred_arr[idx]
        # Skip if sample lacks a class
        if len(np.unique(b_true)) < K:
            continue
        bs_macro_f1.append(f1_score(b_true, b_pred, average="macro"))
        bs_bal_acc.append(balanced_accuracy_score(b_true, b_pred))

    ci_f1 = (
        round(float(np.percentile(bs_macro_f1, 2.5)), 4),
        round(float(np.percentile(bs_macro_f1, 97.5)), 4),
    ) if len(bs_macro_f1) > 50 else (macro_f1, macro_f1)

    ci_bal_acc = (
        round(float(np.percentile(bs_bal_acc, 2.5)), 4),
        round(float(np.percentile(bs_bal_acc, 97.5)), 4),
    ) if len(bs_bal_acc) > 50 else (bal_acc, bal_acc)

    return {
        "num_patients": N,
        "num_classes": K,
        "class_names": class_names,
        "macro_f1": round(macro_f1, 4),
        "macro_f1_ci95": ci_f1,
        "balanced_accuracy": round(bal_acc, 4),
        "balanced_accuracy_ci95": ci_bal_acc,
        "accuracy": round(acc, 4),
        "top2_accuracy": round(top2_acc, 4),
        "ece": round(ece, 4),
        "malignant_undercall_rate": round(undercall_info["undercall_rate"], 4),
        "malignant_undercall_count": undercall_info["undercall_count"],
        "total_malignancies": undercall_info["total_malignancies"],
        "confusion_matrix": cm.tolist(),
        "per_class_metrics": per_class,
    }

