"""
CLI runner for Track C External TCIA Validation.
Usage:
    python scripts/run_track_c_experiment.py
"""

from pathlib import Path
import json
import pandas as pd
import torch

from xmai.evaluation.track_c_runner import evaluate_tcia_external, generate_track_c_markdown_report


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = WORKSPACE_ROOT / "results" / "track_c"


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"=== Track C TCIA External Validation [Device: {device}] ===")

    manifest_path = WORKSPACE_ROOT / "data" / "manifests" / "tcia_manifest_v1.csv"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing TCIA manifest: {manifest_path}")

    df = pd.read_csv(manifest_path)
    print(f"Loaded TCIA manifest: {len(df)} series across {df['patient_id'].nunique()} patients.")

    ckpt_path = WORKSPACE_ROOT / "results" / "track_a" / "checkpoint_A1_fold_0.pt"
    if ckpt_path.exists():
        print(f"Using trained Track A checkpoint: {ckpt_path.name}")
    else:
        print("Using ImageNet pretrained A1 weights.")

    report_data = evaluate_tcia_external(
        manifest_df=df,
        workspace_root=WORKSPACE_ROOT,
        device=device,
        checkpoint_path=ckpt_path if ckpt_path.exists() else None,
        results_dir=RESULTS_DIR,
    )

    md_report = generate_track_c_markdown_report(report_data, output_path=RESULTS_DIR / "tcia_external_report.md")
    print("\n" + "=" * 60)
    print(md_report)
    print("=" * 60)
    print(f"\n[OK] Track C evaluation complete. Report saved to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
