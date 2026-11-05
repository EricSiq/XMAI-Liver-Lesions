"""
Selective Classification and Clinical Uncertainty Referral Analysis for XMAI.
Implements:
- Risk-Coverage curve computation (Geifman & El-Yaniv, NeurIPS 2017).
- Area Under Risk-Coverage Curve (AURC) and Excess-AURC (E-AURC).
- Autonomous vs Referral Trade-off: Quantifies the percentage of borderline patients
  safely resolved by Multimodal Fusion vs unimodal image-only baseline at strict clinical risk budgets.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from xmai.data.schemas import PredictionRow


def _trapezoid(y: np.ndarray, x: np.ndarray) -> float:
    """NumPy 1.x / 2.0+ cross-compatible trapezoidal integration."""
    if hasattr(np, "trapezoid"):
        return float(np.trapezoid(y, x))
    elif hasattr(np, "trapz"):
        return float(np.trapz(y, x))
    else:
        return float(np.sum((x[1:] - x[:-1]) * (y[1:] + y[:-1]) / 2.0))


def compute_risk_coverage_curve(
    predictions: List[PredictionRow],
    n_thresholds: int = 100,
) -> Dict[str, Any]:
    """
    Computes risk-coverage curve across confidence thresholds.
    Confidence score is defined as the margin |P(HCC) - P(Hemangioma)|.
    Risk = Error rate on covered patients.
    Coverage = Fraction of cohort with confidence >= threshold.
    
    Guarantees:
    - Empty input safety: Returns empty curve structure with 0.0 metrics.
    - Constant margins: Safely handles degenerate cases without dividing by zero.
    """
    if len(predictions) == 0:
        return {
            "coverages": [],
            "risks": [],
            "aurc": 0.0,
            "opt_aurc": 0.0,
            "e_aurc": 0.0,
            "total_cohort_size": 0,
            "full_coverage_error": 0.0,
        }

    margins = np.array([p.margin for p in predictions])
    errors = np.array([1.0 if p.is_error else 0.0 for p in predictions])
    N = len(predictions)

    # Sort by margin ascending
    sorted_indices = np.argsort(margins)
    sorted_margins = margins[sorted_indices]
    sorted_errors = errors[sorted_indices]

    if sorted_margins.min() == sorted_margins.max():
        thresholds = np.array([sorted_margins.min()])
    else:
        thresholds = np.linspace(sorted_margins.min(), sorted_margins.max(), n_thresholds)
    coverages = []
    risks = []

    for th in thresholds:
        covered_mask = sorted_margins >= th
        num_covered = int(covered_mask.sum())
        if num_covered == 0:
            continue

        coverage = num_covered / N
        risk = float(sorted_errors[covered_mask].mean())

        coverages.append(coverage)
        risks.append(risk)

    coverages = np.array(coverages)
    risks = np.array(risks)

    # Sort coverages ascending for integration
    sort_cov_idx = np.argsort(coverages)
    cov_sorted = coverages[sort_cov_idx]
    risk_sorted = risks[sort_cov_idx]

    # Trapezoidal integration for AURC
    aurc = _trapezoid(risk_sorted, cov_sorted)

    # Optimal risk curve (all errors deferred first)
    total_errors = int(errors.sum())
    opt_risks = []
    for c in cov_sorted:
        covered_n = int(round(c * N))
        uncovered_n = N - covered_n
        remaining_errs = max(0, total_errors - uncovered_n)
        opt_risks.append(remaining_errs / max(1, covered_n))
    opt_aurc = _trapezoid(np.array(opt_risks), cov_sorted)
    e_aurc = aurc - opt_aurc  # Excess AURC

    return {
        "coverages": cov_sorted.tolist(),
        "risks": risk_sorted.tolist(),
        "aurc": aurc,
        "opt_aurc": opt_aurc,
        "e_aurc": max(0.0, e_aurc),
        "total_cohort_size": N,
        "full_coverage_error": float(errors.mean()),
    }


def compute_clinical_referral_rate(
    predictions: List[PredictionRow],
    target_risk: float = 0.005,
) -> Dict[str, float]:
    """
    Finds the maximum coverage (and required referral rate) to guarantee
    an error rate no greater than target_risk (default: 0.5% clinical safety budget).
    """
    if len(predictions) == 0:
        return {
            "target_risk": target_risk,
            "max_autonomous_coverage": 0.0,
            "required_referral_rate": 1.0,
            "full_coverage_risk": 0.0,
        }

    rc = compute_risk_coverage_curve(predictions, n_thresholds=200)
    covs = np.array(rc["coverages"])
    risks = np.array(rc["risks"])

    valid_mask = risks <= target_risk
    if not np.any(valid_mask):
        # Even at lowest coverage, risk exceeds target
        max_coverage = 0.0
        referral_rate = 1.0
    else:
        # Highest coverage satisfying target_risk
        max_coverage = float(np.max(covs[valid_mask]))
        referral_rate = float(1.0 - max_coverage)

    return {
        "target_risk": target_risk,
        "max_autonomous_coverage": max_coverage,
        "required_referral_rate": referral_rate,
        "full_coverage_risk": rc["full_coverage_error"],
    }


def compare_multimodal_referral_efficiency(
    preds_dict: Dict[str, List[PredictionRow]],
    target_risk: float = 0.005,
) -> pd.DataFrame:
    """
    Generates comparative referral table comparing unimodal and multimodal models
    at strict clinical risk tolerances.
    """
    rows = []
    for mid, preds in preds_dict.items():
        ref_metrics = compute_clinical_referral_rate(preds, target_risk=target_risk)
        rc_metrics = compute_risk_coverage_curve(preds, n_thresholds=100)
        rows.append({
            "Model": mid,
            "Autonomous Coverage (%)": round(ref_metrics["max_autonomous_coverage"] * 100, 2),
            "Referral Rate (%)": round(ref_metrics["required_referral_rate"] * 100, 2),
            "AURC (x10^-3)": round(rc_metrics["aurc"] * 1e3, 3),
            "E-AURC (x10^-3)": round(rc_metrics["e_aurc"] * 1e3, 3),
            "Zero-Deferral Error (%)": round(rc_metrics["full_coverage_error"] * 100, 2),
        })

    return pd.DataFrame(rows)
