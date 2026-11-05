#!/usr/bin/env python3
"""
CLI training script for 5-class focal liver lesion multimodal differential diagnosis.

Usage:
    python scripts/train_5class.py --model M5_gated --epochs 3
    python scripts/train_5class.py --model M5_hierarchical --epochs 3
    python scripts/train_5class.py --model M5_evidential --epochs 3
"""

import argparse
from pathlib import Path
import sys
import torch

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from xmai.training.multiclass_runner import run_multiclass_cross_validation


def main():
    parser = argparse.ArgumentParser(description="Train 5-class FLL multimodal differential diagnosis pipeline.")
    parser.add_argument("--model", type=str, default="M5_gated", choices=["M5_gated", "M5_hierarchical", "M5_evidential"])
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs per fold")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate")
    parser.add_argument("--num-classes", type=int, default=5, choices=[5, 6], help="Number of classes (5 or 6)")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    print(f"=== XMAI 5-Class Multimodal Differential Diagnosis Training ===")
    print(f"  Model Architecture: {args.model}")
    print(f"  Classes:            {args.num_classes}")
    print(f"  Epochs per fold:    {args.epochs}")
    print(f"  Accelerator:        {args.device}")

    report = run_multiclass_cross_validation(
        model_type=args.model,
        num_classes=args.num_classes,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        device=args.device,
    )

    print("\n=== Final 5-Fold Stratified Cross-Validation Summary ===")
    print(f"  Total Patients Evaluated: {report['num_patients']}")
    print(f"  Macro-Averaged F1:        {report['macro_f1']} (95% CI: {report['macro_f1_ci95']})")
    print(f"  Balanced Accuracy:        {report['balanced_accuracy']} (95% CI: {report['balanced_accuracy_ci95']})")
    print(f"  Top-2 Accuracy:           {report['top2_accuracy']}")
    print(f"  Expected Calibration Error: {report['ece']}")
    print(f"  Malignant Under-Call Rate: {report['malignant_undercall_rate']} ({report['malignant_undercall_count']}/{report['total_malignancies']})")
    print(f"  Report saved to: results/multiclass/eval_report_{args.model}.json")


if __name__ == "__main__":
    main()

