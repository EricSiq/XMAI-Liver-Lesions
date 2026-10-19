"""
CLI runner for Track B Temporal CEUS Evaluation (SYSU-CEUS Demo).
Enforces tasks.md Section 4 start conditions:
- Dataset completeness = demo_only
- Exports temporal attention profiles and comparative macro-F1
"""

from pathlib import Path
import json
import pandas as pd
import torch

from xmai.training.track_b_runner import run_track_b_demo_evaluation


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = WORKSPACE_ROOT / "results" / "track_b"


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"=== Track B Temporal CEUS Evaluation [Device: {device}] ===")

    manifest_path = WORKSPACE_ROOT / "data" / "manifests" / "sysu_demo_manifest_v1.csv"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")

    df = pd.read_csv(manifest_path)
    print(f"Loaded SYSU demo manifest with {len(df)} cine videos across classes: {df['label'].value_counts().to_dict()}")

    results = run_track_b_demo_evaluation(
        manifest_df=df,
        workspace_root=WORKSPACE_ROOT,
        device=device,
        models=["B1", "B2", "B3", "B4"],
        results_dir=RESULTS_DIR,
    )

    print("\n--- Track B Summary Results ---")
    print(f"Dataset Completeness: {results['dataset_completeness']}")
    print(f"Status Note: {results['status']}")
    print("Models Evaluated:")
    for mid, res in results["models"].items():
        print(f"  [{mid}] Macro-F1: {res['macro_f1']} | Temporal Attention: {res['has_temporal_attention']}")

    print(f"\n[OK] Results and temporal attention profiles written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
