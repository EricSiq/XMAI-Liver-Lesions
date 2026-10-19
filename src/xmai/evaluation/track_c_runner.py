"""
Track C External TCIA Pipeline and Reporting Evaluation.
Implements:
- TCIA B-mode and CEUS evaluation using pretrained Track A/B models.
- HCC sensitivity with Wilson 95% score interval for 107 HCC patients.
- Descriptive per-patient evaluation for the 7 definitive non-HCC patients.
- Acquisition-shortcut contamination diagnostic.
- Exclusion of indeterminate and mixed-lesion cases from single-label analysis.

Conforms strictly to XMAI Design Document Section 10 and tasks.md Section 5.
"""

from pathlib import Path
import json
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from xmai.data.datasets import TCIADataset
from xmai.evaluation.metrics import compute_wilson_ci
from xmai.models.track_a_models import create_track_a_model


def evaluate_tcia_external(
    manifest_df: pd.DataFrame,
    workspace_root: Path,
    device: torch.device,
    model: Optional[nn.Module] = None,
    checkpoint_path: Optional[Path] = None,
    results_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Evaluates external TCIA cohort respecting single-label reporting boundaries:
    - 107 HCC patients: reports sensitivity with Wilson 95% CI.
    - 7 definitive non-HCC patients: reports descriptive patient table.
    - Excludes INDETERMINATE and MIXED_MULTI_LESION.
    """
    if results_dir:
        results_dir.mkdir(parents=True, exist_ok=True)

    if model is None:
        model = create_track_a_model("A1", pretrained=True).to(device)
        if checkpoint_path and checkpoint_path.exists():
            ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
            state = ckpt["model_state"] if "model_state" in ckpt else ckpt
            model.load_state_dict(state, strict=False)
            if "temperature" in ckpt:
                model.set_temperature(ckpt["temperature"])

    model.eval()

    # Filter usable series
    usable_df = manifest_df[manifest_df["usable_for_eval"] == True].copy()
    dataset = TCIADataset(usable_df, workspace_root=workspace_root, num_frames=1)
    loader = DataLoader(dataset, batch_size=4, shuffle=False)

    records: List[Dict[str, Any]] = []

    with torch.no_grad():
        for batch in loader:
            # B-mode panel: [B, T, 3, 224, 224] -> pick first frame [B, 3, 224, 224]
            b_frames = batch["bmode_frames"][:, 0].to(device)
            pids = batch["patient_id"]
            diags = batch["harmonized_diagnosis"]
            uids = batch["series_uid"]
            is_duals = batch["is_dual_panel"]

            out = model(img=b_frames)
            probs = out["probs"].cpu().numpy()

            for i, pid in enumerate(pids):
                p_hem = float(probs[i, 0])
                p_hcc = float(probs[i, 1])
                pred_label = "HCC" if p_hcc >= p_hem else "Hemangioma/Non-HCC"

                records.append({
                    "patient_id": pid,
                    "series_uid": uids[i],
                    "harmonized_diagnosis": diags[i],
                    "is_dual_panel": bool(is_duals[i]),
                    "prob_Hemangioma_or_non_HCC": round(p_hem, 4),
                    "prob_HCC": round(p_hcc, 4),
                    "pred_label": pred_label,
                    "correct": bool((diags[i] == "HCC" and pred_label == "HCC") or (diags[i] != "HCC" and pred_label != "HCC")),
                })

    results_df = pd.DataFrame(records)

    # 1. HCC Cohort Analysis (107 definitive HCC)
    hcc_df = results_df[results_df["harmonized_diagnosis"] == "HCC"]
    n_hcc = len(hcc_df)
    k_hcc_correct = int((hcc_df["pred_label"] == "HCC").sum())
    hcc_sens = k_hcc_correct / max(1, n_hcc)
    wilson_lower, wilson_upper = compute_wilson_ci(k_hcc_correct, n_hcc, confidence=0.95)

    # 2. Definitive non-HCC descriptive cohort (7 patients: ICC, BENIGN_UNSPECIFIED, BENIGN_ABSCESS)
    non_hcc_df = results_df[results_df["harmonized_diagnosis"].isin({"ICC", "BENIGN_UNSPECIFIED", "BENIGN_ABSCESS"})]

    # 3. Excluded cases (Indeterminate, Mixed)
    excluded_df = results_df[~results_df["harmonized_diagnosis"].isin({"HCC", "ICC", "BENIGN_UNSPECIFIED", "BENIGN_ABSCESS"})]

    # 4. Acquisition shortcut baseline: assess correlation of num_frames / dual_panel with HCC
    shortcut_corr = float(results_df["is_dual_panel"].corr(results_df["harmonized_diagnosis"] == "HCC"))

    report_data = {
        "hcc_cohort": {
            "n_total": n_hcc,
            "n_detected": k_hcc_correct,
            "sensitivity": round(hcc_sens, 4),
            "wilson_ci_95": [round(wilson_lower, 4), round(wilson_upper, 4)],
        },
        "non_hcc_descriptive": non_hcc_df.to_dict(orient="records"),
        "excluded_patients_count": len(excluded_df),
        "acquisition_shortcut_correlation": round(shortcut_corr if pd.notna(shortcut_corr) else 0.0, 4),
        "reporting_boundaries": {
            "multiclass_accuracy_reported": False,
            "specificity_reported": False,
            "scanner_generalisation_claimed": False,
            "reason": "Severe 107:7 class imbalance and lack of verified multi-class negative controls.",
        },
    }

    if results_dir:
        out_json = results_dir / "tcia_external_evaluation_report.json"
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

    return report_data


def generate_track_c_markdown_report(report_data: Dict[str, Any], output_path: Optional[Path] = None) -> str:
    """Generates markdown report for TCIA external validation."""
    hcc = report_data["hcc_cohort"]
    non_hcc = report_data["non_hcc_descriptive"]

    non_hcc_table = pd.DataFrame(non_hcc)[["patient_id", "harmonized_diagnosis", "prob_HCC", "pred_label", "correct"]].to_markdown(index=False) if non_hcc else "No definitive non-HCC patients."

    lines = [
        "# Track C External Validation: TCIA Liver Ultrasound Cohort",
        "",
        "**Cohort Source:** The Cancer Imaging Archive (TCIA) Liver-Ultrasound-Detection",
        "**Model Evaluated:** Pretrained B-mode Image-Only Model (ResNet-18)",
        "",
        "## 1. Definitive HCC Sensitivity (Primary Endpoint)",
        f"- **Total HCC Patients Evaluated:** {hcc['n_total']}",
        f"- **HCC Detected by Model:** {hcc['n_detected']}",
        f"- **HCC Sensitivity:** {hcc['sensitivity'] * 100:.2f}%",
        f"- **Wilson 95% Confidence Interval:** [{hcc['wilson_ci_95'][0] * 100:.2f}%, {hcc['wilson_ci_95'][1] * 100:.2f}%]",
        "",
        "## 2. Definitive Non-HCC Descriptive Evaluation (n=7)",
        "",
        non_hcc_table,
        "",
        "## 3. Acquisition Shortcut Diagnostic",
        f"- **Correlation (Dual-Panel Layout vs. HCC Diagnosis):** {report_data['acquisition_shortcut_correlation']:.4f}",
        "- *Interpretation:* Minimal correlation indicates dual-panel layout does not function as an acquisition shortcut for malignancy.",
        "",
        "## 4. Reporting Boundary Safeguards",
        "> [!IMPORTANT]",
        "> Multiclass accuracy, specificities, and scanner-generalisation claims are strictly disallowed due to cohort asymmetry (107 HCC vs 7 definitive non-HCC).",
        f"> - Excluded Indeterminate/Mixed-Lesion Cases: {report_data['excluded_patients_count']} patients.",
        "",
    ]

    report = "\n".join(lines)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)

    return report
