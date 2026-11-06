"""
Script to generate publication-grade evaluation figures from saved predictions.
Generates:
1. Multi-model ROC Curves (A1, A2, A4, A6)
2. Reliability Diagrams (Calibration Curves & ECE)
3. Hypothesis H1 Low-Margin Decile Rescue/Harm Breakdown
4. Visual Figures Report in artifacts/evaluation_figures/

Conforms to XMAI Phase 6 Quality Assurance.
"""

from pathlib import Path
import json
import numpy as np

from xmai.data.schemas import PredictionRow
from xmai.evaluation.track_a_analysis import analyze_low_margin_decile
from xmai.evaluation.visualization import (
    plot_multimodel_roc_curves,
    plot_reliability_diagrams,
    plot_hypothesis_h1_breakdown,
)


def main() -> None:
    results_dir = Path("results/track_a").resolve()
    out_dir = Path("artifacts/evaluation_figures").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== Generating XMAI Evaluation Figures ===")
    models = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9"]
    preds_dict = {}

    for m in models:
        json_file = results_dir / f"oof_predictions_{m}.json"
        if not json_file.exists():
            json_file = results_dir / f"oof_predictions_{m}_late_fusion.json"
        if not json_file.exists():
            print(f"[WARN] File not found: {json_file}")
            continue
        with open(json_file, "r") as f:
            raw_data = json.load(f)
        preds = [PredictionRow(**item) for item in raw_data]
        preds_dict[m] = preds
        print(f"Loaded {len(preds)} predictions for model {m}")

    if not preds_dict:
        print("[ERROR] No predictions found to visualize!")
        return

    # 1. Multi-model ROC Curves
    roc_path = out_dir / "multimodel_roc_curves.png"
    plot_multimodel_roc_curves(preds_dict, roc_path)
    print(f"[OK] ROC curves saved to {roc_path}")

    # 2. Reliability Diagrams
    rel_path = out_dir / "reliability_diagrams.png"
    plot_reliability_diagrams(preds_dict, rel_path)
    print(f"[OK] Reliability diagrams saved to {rel_path}")

    # 3. Hypothesis H1 Breakdown
    if "A1" in preds_dict and "A4" in preds_dict:
        h1_data = analyze_low_margin_decile(preds_dict["A1"], preds_dict["A4"])
        h1_path = out_dir / "hypothesis_h1_breakdown.png"
        plot_hypothesis_h1_breakdown(h1_data, h1_path)
        print(f"[OK] Hypothesis H1 figure saved to {h1_path}")

    # 4. Write Summary Markdown
    md_path = out_dir / "evaluation_figures_report.md"
    with open(md_path, "w") as f:
        f.write("# XMAI Evaluation Figures & Publication Diagnostics\n\n")
        f.write("All figures are automatically derived from out-of-fold cross-validation predictions.\n\n")
        f.write("## 1. Multi-Model ROC Curves\n")
        f.write(f"![ROC Curves]({roc_path.name})\n\n")
        f.write("## 2. Calibration & Reliability Profiles\n")
        f.write(f"![Reliability Diagrams]({rel_path.name})\n\n")
        f.write("## 3. Hypothesis H1: Clinical Context Benefit by B-mode Margin\n")
        f.write(f"![Hypothesis H1 Breakdown]({h1_path.name})\n\n")

    print(f"[OK] Evaluation figures report saved to {md_path}")


if __name__ == "__main__":
    main()
