"""
CLI runner for Track A Multimodal Baseline and Fusion Experiment.
Usage:
    python scripts/run_track_a_experiment.py --smoke
    python scripts/run_track_a_experiment.py --models A1 A2 A4 A6 A7 --epochs 5
"""

import argparse
from pathlib import Path
import json
import pandas as pd
import torch

from xmai.data.schemas import PredictionRow
from xmai.evaluation.track_a_analysis import generate_track_a_summary_report
from xmai.training.track_a_runner import (
    run_track_a_fold,
    run_track_a_late_fusion_cv,
)


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = WORKSPACE_ROOT / "results" / "track_a"


def main():
    parser = argparse.ArgumentParser(description="Track A Multimodal Baseline & Fusion Runner")
    parser.add_argument("--manifest", type=str, default="data/manifests/smc_manifest_v1.csv")
    parser.add_argument("--models", nargs="+", default=["A1", "A2", "A4", "A6"], help="Models to evaluate: A1, A2, A3, A4, A5, A6, A7")
    parser.add_argument("--folds", nargs="+", type=int, default=[0, 1, 2, 3, 4], help="Folds to run (default: 0 1 2 3 4)")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs per fold")
    parser.add_argument("--batch_size", type=int, default=16, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--device", type=str, default="auto", help="Compute device: auto, cuda, or cpu")
    parser.add_argument("--smoke", action="store_true", help="Run quick 1-fold 1-epoch smoke test")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.device == "auto":
        device_str = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device_str = args.device
    device = torch.device(device_str)
    print(f"=== Track A Multimodal Study [Device: {device}] ===")

    manifest_path = WORKSPACE_ROOT / args.manifest
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    df = pd.read_csv(manifest_path)
    print(f"Loaded manifest with {len(df)} images across {df['patient_id'].nunique()} patients.")

    target_folds = [0] if args.smoke else args.folds
    epochs = 1 if args.smoke else args.epochs
    models_to_run = ["A1", "A2", "A4", "A6"] if args.smoke else args.models

    print(f"Target Folds: {target_folds} | Epochs per fold: {epochs} | Models: {models_to_run}")

    all_models_preds = {}

    for mid in models_to_run:
        if mid == "A6":
            continue  # A6 is computed via late fusion after A1 and A2 are completed
        print(f"\n--- Running Training & Evaluation for Model {mid} ---")
        model_preds = []
        for f in target_folds:
            print(f"-> Fold {f} (epochs={epochs})...")
            fold_preds = run_track_a_fold(
                manifest_df=df,
                fold=f,
                model_id=mid,
                workspace_root=WORKSPACE_ROOT,
                device=device,
                epochs=epochs,
                lr=args.lr,
                batch_size=args.batch_size,
                seed=args.seed,
                results_dir=RESULTS_DIR,
            )
            model_preds.extend(fold_preds)

        all_models_preds[mid] = model_preds
        # Save OOF predictions
        oof_path = RESULTS_DIR / f"oof_predictions_{mid}.json"
        with open(oof_path, "w", encoding="utf-8") as f:
            json.dump([r.model_dump() for r in model_preds], f, indent=2)
        print(f"[OK] Model {mid} complete: saved {len(model_preds)} patient predictions to {oof_path.name}")

    # Compute A6 Late Fusion if requested and A1, A2 available
    if "A6" in models_to_run and "A1" in all_models_preds and "A2" in all_models_preds:
        print("\n--- Computing A6 Late Fusion (0.5 * P(A1) + 0.5 * P(A2)) ---")
        a6_preds = run_track_a_late_fusion_cv(
            a1_preds=all_models_preds["A1"],
            a2_preds=all_models_preds["A2"],
            weight_a1=0.5,
            results_dir=RESULTS_DIR,
        )
        all_models_preds["A6"] = a6_preds
        print(f"[OK] A6 Late Fusion complete: saved {len(a6_preds)} predictions.")

    # Generate Summary Report
    report_file = RESULTS_DIR / "track_a_summary_report.md"
    report_content = generate_track_a_summary_report(all_models_preds, output_path=report_file)
    print("\n" + "=" * 60)
    print(report_content)
    print("=" * 60)
    print(f"\n[OK] Track A execution finished successfully. Report saved to {report_file}")


if __name__ == "__main__":
    main()
