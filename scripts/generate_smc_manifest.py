#!/usr/bin/env python3
"""
CLI script to audit SMC-LUD clean images, join patient metadata,
generate stratified patient-level 5-fold CV splits, and save the manifest.
"""

import argparse
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table

from xmai.data.smc_manifest import generate_smc_manifest

console = Console()


def main():
    parser = argparse.ArgumentParser(description="Generate SMC-LUD clean cohort manifest with patient-stratified folds.")
    parser.add_argument("--workspace-root", type=str, default=".", help="Project workspace root directory")
    parser.add_argument("--output", type=str, default="data/manifests/smc_manifest_v1.csv", help="Output manifest CSV path")
    parser.add_argument("--report-json", type=str, default="artifacts/smc_audit_report.json", help="Output audit report path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for fold stratification")
    args = parser.parse_args()

    workspace_root = Path(args.workspace_root).resolve()
    output_path = workspace_root / args.output
    report_path = workspace_root / args.report_json

    console.print(f"[bold cyan]Auditing SMC-LUD and generating manifest from:[/bold cyan] {workspace_root}")
    manifest_df, audit_stats = generate_smc_manifest(
        workspace_root=workspace_root,
        output_manifest_path=output_path,
        seed=args.seed,
    )

    # Save audit report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(audit_stats, f, indent=2)

    # Display Pretty Rich Tables
    console.print("\n[bold green][OK] SMC Manifest Generated Successfully![/bold green]")
    console.print(f"Manifest Path: [cyan]{output_path}[/cyan]")
    console.print(f"Audit Report:  [cyan]{report_path}[/cyan]")

    # Overview Table
    overview = Table(title="SMC-LUD Clean Cohort Overview")
    overview.add_column("Metric", style="bold")
    overview.add_column("Value", style="magenta")
    overview.add_row("Total Patients", str(audit_stats["total_patients"]))
    overview.add_row("Total Clean Images", str(audit_stats["total_images"]))
    overview.add_row("Patients: HCC / Hemangioma", f"{audit_stats['patients_by_class'].get('HCC', 0)} / {audit_stats['patients_by_class'].get('Hemangioma', 0)}")
    overview.add_row("Images: HCC / Hemangioma", f"{audit_stats['images_by_class'].get('HCC', 0)} / {audit_stats['images_by_class'].get('Hemangioma', 0)}")
    overview.add_row("Images per Patient (Min / Median / Max)", f"{audit_stats['images_per_patient']['min']} / {audit_stats['images_per_patient']['median']} / {audit_stats['images_per_patient']['max']}")
    overview.add_row("Patients Missing Age", str(audit_stats["patients_missing_age"]))
    overview.add_row("Patients Missing Sex", str(audit_stats["patients_missing_sex"]))
    overview.add_row("Unmatched Folders (Excluded)", str(audit_stats["unmatched_folders"]))
    console.print(overview)

    # Fold Distribution Table
    fold_table = Table(title="Patient-Level 5-Fold Stratification")
    fold_table.add_column("Fold Index", justify="center")
    fold_table.add_column("HCC Patients", justify="right")
    fold_table.add_column("Hem Patients", justify="right")
    fold_table.add_column("Total Patients", justify="right")
    fold_table.add_column("Total Images", justify="right")

    pat_folds = audit_stats["patients_per_fold"]
    img_folds = audit_stats["images_per_fold"]

    for f_idx in range(5):
        hcc_p = pat_folds["HCC"].get(f_idx, 0)
        hem_p = pat_folds["Hemangioma"].get(f_idx, 0)
        tot_p = hcc_p + hem_p
        hcc_img = img_folds["HCC"].get(f_idx, 0)
        hem_img = img_folds["Hemangioma"].get(f_idx, 0)
        tot_img = hcc_img + hem_img
        fold_table.add_row(str(f_idx), str(hcc_p), str(hem_p), str(tot_p), str(tot_img))

    console.print(fold_table)


if __name__ == "__main__":
    main()
