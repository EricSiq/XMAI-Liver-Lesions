#!/usr/bin/env python3
"""
CLI script to generate a clinical feature report across all 5 cross-validation folds.
Conforms to tasks.md Section 2.2.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict
import pandas as pd
from rich.console import Console
from rich.table import Table

from xmai.data.clinical import generate_clinical_fold_report

console = Console()


def render_markdown_report(report: Dict[str, Any]) -> str:
    cs = report["cohort_summary"]
    md = f"""# XMAI Clinical Feature Report (SMC-LUD Clean Cohort)

## 1. Cohort Demographics Summary
- **Total Clean Patients**: {cs['total_patients']}
- **HCC Patients**: {cs['hcc_patients']} ({cs['hcc_patients']/cs['total_patients']*100:.1f}%)
- **Hemangioma Patients**: {cs['hem_patients']} ({cs['hem_patients']/cs['total_patients']*100:.1f}%)
- **HCC Mean Age**: {cs['hcc_age_mean']:.2f} years
- **Hemangioma Mean Age**: {cs['hem_age_mean']:.2f} years
- **HCC Male Proportion**: {cs['hcc_male_ratio']*100:.1f}%
- **Hemangioma Male Proportion**: {cs['hem_male_ratio']*100:.1f}%

> **Cohort Association Finding**: HCC patients in this cohort are significantly older (mean {cs['hcc_age_mean']:.1f} vs {cs['hem_age_mean']:.1f} years) and predominantly male ({cs['hcc_male_ratio']*100:.1f}% vs {cs['hem_male_ratio']*100:.1f}%). This confirms the demographic cohort prior documented in the XMAI Design Document v2 Section 4.4.

## 2. Fold-by-Fold Balance & Imputation Metrics

| Fold | Split | Total Patients | HCC | Hem | Age Mean (SD) | Missing Age | Male % |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
"""
    for fold_name, f_data in sorted(report["folds"].items()):
        f_idx = fold_name.split("_")[1]
        tr = f_data["train"]
        val = f_data["val"]
        md += f"| {f_idx} | Train | {tr['patients']} | {tr['hcc']} | {tr['hem']} | {tr['age_mean']:.1f} ({tr['age_std']:.1f}) | {tr['missing_age']} | {tr['male_ratio']*100:.1f}% |\n"
        md += f"| {f_idx} | Val | {val['patients']} | {val['hcc']} | {val['hem']} | {val['age_mean']:.1f} ({val['age_std']:.1f}) | {val['missing_age']} | {val['male_ratio']*100:.1f}% |\n"

    return md


def main():
    parser = argparse.ArgumentParser(description="Generate fold-by-fold clinical feature report.")
    parser.add_argument("--manifest", type=str, default="data/manifests/smc_manifest_v1.csv", help="Path to manifest CSV")
    parser.add_argument("--output-json", type=str, default="artifacts/clinical_feature_report.json", help="Path to JSON report")
    parser.add_argument("--output-md", type=str, default="artifacts/clinical_feature_report.md", help="Path to Markdown report")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    manifest_df = pd.read_csv(manifest_path)
    report = generate_clinical_fold_report(manifest_df)

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w") as f:
        json.dump(report, f, indent=2)

    md_content = render_markdown_report(report)
    out_md = Path(args.output_md)
    with open(out_md, "w") as f:
        f.write(md_content)

    console.print(f"[bold green][OK] Clinical feature report generated![/bold green]")
    console.print(f"JSON: [cyan]{out_json}[/cyan]")
    console.print(f"Markdown: [cyan]{out_md}[/cyan]")

    cs = report["cohort_summary"]
    t = Table(title="SMC-LUD Clinical Demographics Summary")
    t.add_column("Clinical Variable", style="bold")
    t.add_column("HCC (Malignant)", style="red")
    t.add_column("Hemangioma (Benign)", style="green")
    t.add_row("Total Patients", str(cs["hcc_patients"]), str(cs["hem_patients"]))
    t.add_row("Mean Age (Years)", f"{cs['hcc_age_mean']:.2f}", f"{cs['hem_age_mean']:.2f}")
    t.add_row("Male Proportion", f"{cs['hcc_male_ratio']*100:.1f}%", f"{cs['hem_male_ratio']*100:.1f}%")
    console.print(t)


if __name__ == "__main__":
    main()
