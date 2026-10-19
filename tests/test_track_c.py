"""
Unit tests for Phase 5 Track C TCIA external evaluation and reporting boundaries.
"""

from pathlib import Path
import pandas as pd
import pytest
import torch

from xmai.evaluation.track_c_runner import evaluate_tcia_external, generate_track_c_markdown_report


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def test_tcia_external_evaluation(tmp_path):
    manifest_path = WORKSPACE_ROOT / "data" / "manifests" / "tcia_manifest_v1.csv"
    assert manifest_path.exists()
    df = pd.read_csv(manifest_path)

    # Pick 2 usable HCC and 1 non-HCC
    sample_df = pd.concat([
        df[df["harmonized_diagnosis"] == "HCC"].head(2),
        df[df["harmonized_diagnosis"] != "HCC"].head(1),
    ]).reset_index(drop=True)

    device = torch.device("cpu")
    results = evaluate_tcia_external(
        manifest_df=sample_df,
        workspace_root=WORKSPACE_ROOT,
        device=device,
        results_dir=tmp_path,
    )

    assert "hcc_cohort" in results
    assert "wilson_ci_95" in results["hcc_cohort"]
    w_low, w_high = results["hcc_cohort"]["wilson_ci_95"]
    assert 0.0 <= w_low <= w_high <= 1.0

    assert results["reporting_boundaries"]["multiclass_accuracy_reported"] is False
    assert results["reporting_boundaries"]["specificity_reported"] is False

    md_report = generate_track_c_markdown_report(results, output_path=tmp_path / "report.md")
    assert "Definitive HCC Sensitivity" in md_report
    assert (tmp_path / "report.md").exists()
