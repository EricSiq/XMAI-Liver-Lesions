"""
Patient-level prediction aggregation and metric derivation.
Conforms strictly to Decision D-14 and AI-15:
- Computes arithmetic mean of calibrated per-image class probability vectors for each patient.
- Derives margin (top-1 minus top-2 probability).
- Identifies low-margin subset (lowest decile) for hypothesis H1 evaluation.
- Identifies error set.
- Validates each output row using PredictionRow schema.
"""

from typing import Any, Dict, List
import numpy as np
import pandas as pd

from xmai.data.datasets import INT_TO_LABEL
from xmai.data.schemas import PredictionRow


def aggregate_patient_predictions(
    image_preds_df: pd.DataFrame,
    track: str = "A",
    fold: int = 0,
    seed: int = 42,
    model_id: str = "A4_gated_fusion",
    modality_mask: List[int] = None,
) -> List[PredictionRow]:
    """
    Aggregates image-level predictions to patient-level endpoints.
    Args:
        image_preds_df: DataFrame containing [patient_id, true_label, prob_Hemangioma, prob_HCC]
    Returns:
        List of validated PredictionRow objects.
    """
    if modality_mask is None:
        modality_mask = [1, 0, 1]

    patient_rows: List[Dict[str, Any]] = []

    # Group by patient_id
    grouped = image_preds_df.groupby("patient_id")

    for pat_id, group in grouped:
        true_label = group["true_label"].iloc[0]
        prob_hem = float(group["prob_Hemangioma"].mean())
        prob_hcc = float(group["prob_HCC"].mean())

        # Normalize to ensure exact sum to 1.0 within tolerance
        tot = prob_hem + prob_hcc
        if tot > 0:
            prob_hem /= tot
            prob_hcc /= tot
        else:
            prob_hem = 0.5
            prob_hcc = 0.5

        pred_label = "HCC" if prob_hcc >= prob_hem else "Hemangioma"
        margin = float(abs(prob_hcc - prob_hem))
        is_error = bool(pred_label != true_label)

        patient_rows.append({
            "patient_id": str(pat_id),
            "track": track,
            "fold": fold,
            "seed": seed,
            "model_id": model_id,
            "true_label": str(true_label),
            "pred_label": pred_label,
            "prob_vector": {"Hemangioma": round(prob_hem, 6), "HCC": round(prob_hcc, 6)},
            "margin": round(margin, 6),
            "is_calibrated": True,
            "is_error": is_error,
            "modality_mask": modality_mask,
        })

    # Determine low-margin threshold (bottom 10th percentile of margins across the cohort)
    margins = [r["margin"] for r in patient_rows]
    low_margin_thresh = float(np.percentile(margins, 10)) if len(margins) > 0 else 0.1

    validated_predictions: List[PredictionRow] = []
    for r in patient_rows:
        r["is_low_margin"] = bool(r["margin"] <= low_margin_thresh)
        row_obj = PredictionRow(**r)
        validated_predictions.append(row_obj)

    return validated_predictions
