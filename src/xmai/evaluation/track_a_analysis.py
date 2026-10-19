"""
Track A Comparative Analysis & Hypothesis H1 Testing.
Implements:
- Rescue, harm, and net gain computation.
- Image-only error set analysis.
- Low-margin decile analysis for Hypothesis H1.
- Paired bootstrap confidence intervals (2,000 resamples).
- McNemar test for paired discordance.
- Formatted markdown and tabular comparison summaries.
Conforms to XMAI Design Document Section 9.3 and tasks.md Section 3.4.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats

from xmai.data.schemas import PredictionRow
from xmai.evaluation.metrics import compute_bootstrap_ci, compute_mcnemar_test, compute_patient_metrics


def compute_rescue_harm(
    base_preds: List[PredictionRow],
    fusion_preds: List[PredictionRow],
) -> Dict[str, Any]:
    """
    Computes rescue, harm, and net gain between baseline (e.g. A1) and fusion (e.g. A4).
    - Rescue: base error == True and fusion error == False
    - Harm: base error == False and fusion error == True
    - Net gain: Rescue - Harm
    """
    assert len(base_preds) == len(fusion_preds), "Prediction list size mismatch"
    fusion_map = {p.patient_id: p for p in fusion_preds}

    rescue_patients = []
    harm_patients = []
    both_correct = []
    both_error = []

    for b in base_preds:
        f = fusion_map[b.patient_id]
        if b.is_error and not f.is_error:
            rescue_patients.append(b.patient_id)
        elif not b.is_error and f.is_error:
            harm_patients.append(b.patient_id)
        elif not b.is_error and not f.is_error:
            both_correct.append(b.patient_id)
        else:
            both_error.append(b.patient_id)

    n_rescue = len(rescue_patients)
    n_harm = len(harm_patients)
    net_gain = n_rescue - n_harm

    return {
        "n_patients": len(base_preds),
        "rescue_count": n_rescue,
        "harm_count": n_harm,
        "net_gain": net_gain,
        "rescue_patients": rescue_patients,
        "harm_patients": harm_patients,
        "both_correct_count": len(both_correct),
        "both_error_count": len(both_error),
    }


def analyze_low_margin_decile(
    base_preds: List[PredictionRow],
    fusion_preds: List[PredictionRow],
) -> Dict[str, Any]:
    """
    Evaluates Hypothesis H1: Clinical context rescues primarily low-margin B-mode cases.
    Computes rescue and harm inside vs outside the low-margin decile.
    """
    fusion_map = {p.patient_id: p for p in fusion_preds}
    low_margin_base = [b for b in base_preds if b.is_low_margin]
    high_margin_base = [b for b in base_preds if not b.is_low_margin]

    low_margin_fusion = [fusion_map[b.patient_id] for b in low_margin_base]
    high_margin_fusion = [fusion_map[b.patient_id] for b in high_margin_base]

    low_res = compute_rescue_harm(low_margin_base, low_margin_fusion)
    high_res = compute_rescue_harm(high_margin_base, high_margin_fusion)

    # Proportion of all rescues that occurred in low margin
    total_rescues = low_res["rescue_count"] + high_res["rescue_count"]
    pct_rescue_in_low_margin = (
        (low_res["rescue_count"] / total_rescues * 100.0) if total_rescues > 0 else 0.0
    )

    return {
        "low_margin_n": len(low_margin_base),
        "low_margin_rescues": low_res["rescue_count"],
        "low_margin_harms": low_res["harm_count"],
        "low_margin_net_gain": low_res["net_gain"],
        "high_margin_n": len(high_margin_base),
        "high_margin_rescues": high_res["rescue_count"],
        "high_margin_harms": high_res["harm_count"],
        "high_margin_net_gain": high_res["net_gain"],
        "pct_rescues_in_low_margin": round(pct_rescue_in_low_margin, 2),
    }


def compute_paired_bootstrap_difference(
    base_preds: List[PredictionRow],
    fusion_preds: List[PredictionRow],
    metric_fn: Optional[str] = "balanced_accuracy",
    n_bootstraps: int = 2000,
    seed: int = 42,
    alpha: float = 0.05,
) -> Dict[str, float]:
    """
    Computes patient-level paired bootstrap difference:
    Delta = Metric(Fusion) - Metric(Baseline)
    Returns {mean_delta, ci_lower, ci_upper, p_value}.
    """
    assert len(base_preds) == len(fusion_preds), "Length mismatch in paired bootstrap"
    fusion_map = {p.patient_id: p for p in fusion_preds}
    sorted_fusion = [fusion_map[b.patient_id] for b in base_preds]

    rng = np.random.default_rng(seed)
    n = len(base_preds)
    deltas = []

    y_true = np.array([1 if p.true_label == "HCC" else 0 for p in base_preds])
    yp_b = np.array([1 if p.pred_label == "HCC" else 0 for p in base_preds])
    yp_f = np.array([1 if p.pred_label == "HCC" else 0 for p in sorted_fusion])

    rng = np.random.default_rng(seed)
    n = len(base_preds)
    deltas = []

    for _ in range(n_bootstraps):
        idx = rng.integers(0, n, size=n)
        yt, ypb, ypf = y_true[idx], yp_b[idx], yp_f[idx]

        if len(np.unique(yt)) < 2:
            continue

        if metric_fn == "balanced_accuracy":
            sens_b = np.sum((yt == 1) & (ypb == 1)) / max(1, np.sum(yt == 1))
            spec_b = np.sum((yt == 0) & (ypb == 0)) / max(1, np.sum(yt == 0))
            m_b = 0.5 * (sens_b + spec_b)

            sens_f = np.sum((yt == 1) & (ypf == 1)) / max(1, np.sum(yt == 1))
            spec_f = np.sum((yt == 0) & (ypf == 0)) / max(1, np.sum(yt == 0))
            m_f = 0.5 * (sens_f + spec_f)
        elif metric_fn == "accuracy":
            m_b = np.mean(yt == ypb)
            m_f = np.mean(yt == ypf)
        else:
            b_sample = [base_preds[i] for i in idx]
            f_sample = [sorted_fusion[i] for i in idx]
            m_b = compute_patient_metrics(b_sample)[metric_fn]
            m_f = compute_patient_metrics(f_sample)[metric_fn]

        deltas.append(m_f - m_b)

    deltas_arr = np.array(deltas)
    ci_lower = float(np.percentile(deltas_arr, 100.0 * (alpha / 2.0)))
    ci_upper = float(np.percentile(deltas_arr, 100.0 * (1.0 - alpha / 2.0)))
    mean_delta = float(np.mean(deltas_arr))

    # Two-sided empirical p-value for H0: Delta == 0
    p_val = float(2.0 * min(np.mean(deltas_arr <= 0), np.mean(deltas_arr >= 0)))

    return {
        "metric": metric_fn,
        "mean_delta": round(mean_delta, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "p_value": round(p_val, 4),
    }


def generate_track_a_summary_report(
    models_dict: Dict[str, List[PredictionRow]],
    output_path: Optional[Path] = None,
) -> str:
    """
    Generates comprehensive comparative markdown report across all Track A models:
    A1, A2, A3, A4, A5, A6, A7.
    """
    rows_data = []

    for model_id, preds in models_dict.items():
        metrics = compute_patient_metrics(preds)
        acc_ci = compute_bootstrap_ci(preds, metric_key="accuracy")
        bal_ci = compute_bootstrap_ci(preds, metric_key="balanced_accuracy")
        auc_ci = compute_bootstrap_ci(preds, metric_key="auc")

        rows_data.append({
            "Model": model_id,
            "Accuracy (95% CI)": f"{metrics['accuracy']:.3f} [{acc_ci[0]:.3f}, {acc_ci[1]:.3f}]",
            "Balanced Acc (95% CI)": f"{metrics['balanced_accuracy']:.3f} [{bal_ci[0]:.3f}, {bal_ci[1]:.3f}]",
            "Sensitivity": f"{metrics['recall_sensitivity']:.3f}",
            "Specificity": f"{metrics['specificity']:.3f}",
            "AUC (95% CI)": f"{metrics['auc']:.3f} [{auc_ci[0]:.3f}, {auc_ci[1]:.3f}]",
            "Log-Loss": f"{metrics['log_loss']:.3f}",
            "Brier": f"{metrics['brier_score']:.3f}",
            "ECE": f"{metrics['ece']:.3f}",
        })

    df = pd.DataFrame(rows_data)
    md_table = df.to_markdown(index=False)

    report_lines = [
        "# Track A Multimodal Baseline & Fusion Study Summary",
        "",
        "**Cohort:** SMC-LUD Clean Cohort (743 patients: 421 HCC, 322 Hemangioma)",
        "**Evaluation:** Repeated Patient-Stratified 5-Fold Cross-Validation",
        "**Aggregation:** Arithmetic Mean of Calibrated Per-Image Class Probabilities",
        "",
        "## Overall Model Comparison",
        "",
        md_table,
        "",
    ]

    # If A1 and A4 exist, append rescue/harm & H1 analysis
    if "A1" in models_dict and "A4" in models_dict:
        rh = compute_rescue_harm(models_dict["A1"], models_dict["A4"])
        lm = analyze_low_margin_decile(models_dict["A1"], models_dict["A4"])
        mcnemar = compute_mcnemar_test(models_dict["A1"], models_dict["A4"])
        paired_diff = compute_paired_bootstrap_difference(models_dict["A1"], models_dict["A4"])

        report_lines.extend([
            "## Hypothesis H1 Evaluation: Gated Fusion (A4) vs. B-Mode Only (A1)",
            "",
            f"- **Rescue Count (A4 correct, A1 error):** {rh['rescue_count']} patients",
            f"- **Harm Count (A4 error, A1 correct):** {rh['harm_count']} patients",
            f"- **Net Gain:** {rh['net_gain']:+d} patients",
            f"- **McNemar Discordance Test:** Discordant pairs = {mcnemar['rescued_by_a'] + mcnemar['rescued_by_b']} (p-value: {mcnemar['mcnemar_p_value']:.4f})",
            f"- **Paired Balanced Accuracy Difference:** {paired_diff['mean_delta']:+.4f} (95% CI: [{paired_diff['ci_lower']:+.4f}, {paired_diff['ci_upper']:+.4f}], p={paired_diff['p_value']:.4f})",
            "",
            "### Low-Margin Decile Distribution (Hypothesis H1)",
            f"- **Low-Margin Decile Rescues:** {lm['low_margin_rescues']} / {lm['low_margin_n']} (Net Gain: {lm['low_margin_net_gain']:+d})",
            f"- **High-Margin Rescues:** {lm['high_margin_rescues']} / {lm['high_margin_n']} (Net Gain: {lm['high_margin_net_gain']:+d})",
            f"- **Concentration of Rescues in Low-Margin Decile:** {lm['pct_rescues_in_low_margin']}%",
            "",
        ])

    report_content = "\n".join(report_lines)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_content)

    return report_content
