"""
Track B Temporal CEUS Evaluation Runner.
Evaluates B1 (mean), B2 (temporal attention), B3 (BiLSTM), and B4 (arterial-only).
Enforces tasks.md Section 4 safeguards:
- Logs dataset_completeness = demo_only (15 demo videos).
- Disallows temporal clinical claims without physical phase timing.
- Saves temporal attention weights for explainability inspection.
"""

from pathlib import Path
import json
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, f1_score
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

from xmai.data.datasets import SYSUDataset, SYSU_LABEL_TO_INT
from xmai.models.track_b_models import create_track_b_model


INT_TO_SYSU_LABEL = {v: k for k, v in SYSU_LABEL_TO_INT.items()}


def run_track_b_demo_evaluation(
    manifest_df: pd.DataFrame,
    workspace_root: Path,
    device: torch.device,
    models: Optional[List[str]] = None,
    results_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Evaluates Track B temporal models on available SYSU-CEUS video dataset.
    """
    if models is None:
        models = ["B1", "B2", "B3", "B4"]

    if results_dir:
        results_dir.mkdir(parents=True, exist_ok=True)

    dataset = SYSUDataset(manifest_df, workspace_root=workspace_root, num_frames=16, image_size=224)
    loader = DataLoader(dataset, batch_size=2, shuffle=False)

    summary_results: Dict[str, Any] = {
        "dataset_completeness": "demo_only",
        "num_videos": len(manifest_df),
        "status": "statistical_claims_deferred_pending_full_dataset",
        "models": {},
    }

    for mid in models:
        model = create_track_b_model(mid, num_classes=3, pretrained=True).to(device)
        model.eval()

        all_preds = []
        all_targets = []
        temporal_profiles = []

        with torch.no_grad():
            for batch in loader:
                video = batch["video"].to(device)
                targets = batch["label"].to(device)
                pids = batch["patient_id"]
                timestamps = batch["timestamps"].cpu().numpy()

                out = model(video)
                probs = out["probs"].cpu().numpy()
                preds = np.argmax(probs, axis=1)

                all_preds.extend(preds.tolist())
                all_targets.extend(targets.cpu().numpy().tolist())

                if out.get("temporal_weights") is not None:
                    weights = out["temporal_weights"].cpu().numpy()
                    for i, pid in enumerate(pids):
                        temporal_profiles.append({
                            "patient_id": pid,
                            "timestamps": timestamps[i].tolist(),
                            "attention_weights": weights[i].tolist(),
                            "peak_frame_index": int(np.argmax(weights[i])),
                        })

        macro_f1 = float(f1_score(all_targets, all_preds, average="macro", zero_division=0))
        summary_results["models"][mid] = {
            "macro_f1": round(macro_f1, 4),
            "num_evaluated": len(all_preds),
            "has_temporal_attention": bool(len(temporal_profiles) > 0),
        }

        if temporal_profiles and results_dir:
            profile_path = results_dir / f"{mid}_temporal_attention_profiles.json"
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(temporal_profiles, f, indent=2)

    if results_dir:
        report_path = results_dir / "track_b_summary_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(summary_results, f, indent=2)

    return summary_results
