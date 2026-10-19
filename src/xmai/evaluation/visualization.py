"""
Publication-grade Evaluation Visualisation Module for XMAI.
Generates:
1. Multi-Model ROC Curves with AUC intervals
2. Reliability Diagrams (Calibration Curves) with ECE and Confidence Histograms
3. Hypothesis H1 Rescue/Harm Breakdown (Low-Margin Decile Analysis)
4. Modality Gating Weight Distributions across Pathological Cohorts

Conforms to XMAI Design Document Section 9.3 and Phase 6 Quality Assurance.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import roc_curve, auc

from xmai.data.schemas import PredictionRow


def plot_multimodel_roc_curves(
    predictions_dict: Dict[str, List[PredictionRow]],
    output_path: Path,
    title: str = "Multi-Model ROC Curves (Patient-Aggregated)",
) -> None:
    """
    Plots paired ROC curves for multiple models on out-of-fold predictions.
    """
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, ax = plt.subplots(figsize=(8, 6), dpi=300)

    colors = {
        "A1": "#1f77b4",  # Blue
        "A2": "#ff7f0e",  # Orange
        "A3": "#8c564b",  # Brown
        "A4": "#2ca02c",  # Green
        "A5": "#17becf",  # Cyan
        "A6": "#9467bd",  # Purple
        "A7": "#d62728",  # Red
    }
    labels_map = {
        "A1": "A1: B-mode Only",
        "A2": "A2: Clinical Only",
        "A3": "A3: Concat Fusion",
        "A4": "A4: Gated Multimodal Fusion",
        "A5": "A5: FiLM Fusion",
        "A6": "A6: Late Fusion",
        "A7": "A7: Context-Shuffle Control",
    }

    for model_name, preds in predictions_dict.items():
        y_true = np.array([1 if p.true_label == "HCC" else 0 for p in preds])
        y_prob = np.array([p.prob_vector.get("HCC", 0.0) for p in preds])

        fpr, tpr, _ = roc_curve(y_true, y_prob)
        roc_auc = auc(fpr, tpr)
        color = colors.get(model_name, "#333333")
        label = f"{labels_map.get(model_name, model_name)} (AUC = {roc_auc:.3f})"
        ax.plot(fpr, tpr, label=label, color=color, linewidth=2.0)

    # Reference diagonal
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", alpha=0.7, label="Chance (AUC = 0.500)")

    ax.set_xlim([-0.02, 1.02])
    ax.set_ylim([-0.02, 1.02])
    ax.set_xlabel("False Positive Rate (1 - Specificity)", fontsize=12, fontweight="bold")
    ax.set_ylabel("True Positive Rate (Sensitivity)", fontsize=12, fontweight="bold")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    ax.legend(loc="lower right", frameon=True, fontsize=10)
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def plot_reliability_diagrams(
    predictions_dict: Dict[str, List[PredictionRow]],
    output_path: Path,
    n_bins: int = 10,
) -> None:
    """
    Plots reliability diagrams (calibration curve) for evaluated models.
    """
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    n_models = len(predictions_dict)
    fig, axes = plt.subplots(1, n_models, figsize=(5 * n_models, 4.5), dpi=300, sharey=True)

    if n_models == 1:
        axes = [axes]

    for ax, (model_name, preds) in zip(axes, predictions_dict.items()):
        y_true = np.array([1 if p.true_label == "HCC" else 0 for p in preds])
        y_prob = np.array([p.prob_vector.get("HCC", 0.0) for p in preds])

        prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=n_bins, strategy="uniform")

        # Perfectly calibrated diagonal
        ax.plot([0, 1], [0, 1], linestyle="--", color="gray", alpha=0.7, label="Perfect")

        # Calibration curve
        ax.plot(prob_pred, prob_true, marker="s", linewidth=2.0, color="#1f77b4", label="Model")

        # Compute empirical ECE
        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
        bin_idx = np.digitize(y_prob, bin_edges) - 1
        bin_idx = np.clip(bin_idx, 0, n_bins - 1)
        ece = 0.0
        n_samples = len(y_prob)
        for i in range(n_bins):
            mask = bin_idx == i
            if np.any(mask):
                bin_acc = np.mean(y_true[mask])
                bin_conf = np.mean(y_prob[mask])
                ece += (np.sum(mask) / n_samples) * np.abs(bin_acc - bin_conf)

        ax.set_title(f"{model_name} (ECE = {ece:.3f})", fontsize=12, fontweight="bold")
        ax.set_xlabel("Mean Predicted Probability", fontsize=10, fontweight="bold")
        if ax == axes[0]:
            ax.set_ylabel("Empirical True Fraction", fontsize=10, fontweight="bold")
        ax.set_xlim([-0.05, 1.05])
        ax.set_ylim([-0.05, 1.05])
        ax.legend(loc="upper left", frameon=True, fontsize=9)

    plt.suptitle("Reliability Diagrams (Calibration Profiles)", fontsize=14, fontweight="bold", y=1.03)
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_hypothesis_h1_breakdown(
    h1_results: Dict[str, Any],
    output_path: Path,
) -> None:
    """
    Plots the Hypothesis H1 Rescue vs. Harm breakdown across low-margin vs. high-margin deciles.
    """
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, ax = plt.subplots(figsize=(7, 5), dpi=300)

    categories = ["Low-Margin Decile\n(Ambiguous B-mode)", "High-Margin Decile\n(Clear B-mode)"]
    rescues = [h1_results["low_margin_rescues"], h1_results["high_margin_rescues"]]
    harms = [-h1_results["low_margin_harms"], -h1_results["high_margin_harms"]]
    net_gain = [h1_results["low_margin_net_gain"], h1_results["high_margin_net_gain"]]

    x = np.arange(len(categories))
    width = 0.25

    rects1 = ax.bar(x - width, rescues, width, label="Rescues (+)", color="#2ca02c", alpha=0.85)
    rects2 = ax.bar(x, harms, width, label="Harms (-)", color="#d62728", alpha=0.85)
    rects3 = ax.bar(x + width, net_gain, width, label="Net Gain", color="#1f77b4", alpha=0.85)

    ax.axhline(0, color="black", linewidth=1.0)
    ax.set_ylabel("Patient Count", fontsize=12, fontweight="bold")
    ax.set_title("Hypothesis H1 Testing: Clinical Context Benefit by B-mode Margin", fontsize=13, fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=11, fontweight="bold")
    ax.legend(loc="upper right", frameon=True, fontsize=10)

    # Annotate bars
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            y_pos = height if height >= 0 else height - 0.3
            ax.annotate(
                f"{int(height)}",
                xy=(rect.get_x() + rect.get_width() / 2, y_pos),
                xytext=(0, 3 if height >= 0 else -10),
                textcoords="offset points",
                ha="center",
                va="bottom" if height >= 0 else "top",
                fontsize=10,
                fontweight="bold",
            )

    autolabel(rects1)
    autolabel(rects2)
    autolabel(rects3)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
