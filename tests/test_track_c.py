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


def test_wilson_ci_boundary_invariants():
    """Verify Wilson score confidence interval mathematical invariants at extreme boundaries."""
    from xmai.evaluation.metrics import compute_wilson_ci

    # 1. Zero successes (k=0, n=50) -> lower must be approx 0.0, upper strictly positive
    low_0, high_0 = compute_wilson_ci(0, 50, confidence=0.95)
    assert low_0 == pytest.approx(0.0, abs=1e-6)
    assert 0.0 < high_0 <= 0.10

    # 2. Perfect successes (k=50, n=50) -> upper must be 1.0, lower strictly < 1.0
    low_1, high_1 = compute_wilson_ci(50, 50, confidence=0.95)
    assert high_1 == pytest.approx(1.0, abs=1e-6)
    assert 0.90 <= low_1 < 1.0

    # 3. Monotonic narrowing: CI with n=500 must be narrower than CI with n=50 at same proportion
    w_small_low, w_small_high = compute_wilson_ci(40, 50, confidence=0.95)
    w_large_low, w_large_high = compute_wilson_ci(400, 500, confidence=0.95)

    width_small = w_small_high - w_small_low
    width_large = w_large_high - w_large_low
    assert width_large < width_small, "Larger cohort must yield strictly narrower confidence interval"


def test_indeterminate_exclusion_barrier(tmp_path):
    """Indeterminate and mixed multi-lesion cases must be excluded from sensitivity calculation."""
    manifest_path = WORKSPACE_ROOT / "data" / "manifests" / "tcia_manifest_v1.csv"
    df = pd.read_csv(manifest_path)

    # Inject an indeterminate test case
    indet_case = df.head(1).copy()
    indet_case["harmonized_diagnosis"] = "INDETERMINATE"
    indet_case["patient_id"] = "TCIA_INDET_999"

    test_df = pd.concat([df.head(2), indet_case]).reset_index(drop=True)

    results = evaluate_tcia_external(
        manifest_df=test_df,
        workspace_root=WORKSPACE_ROOT,
        device=torch.device("cpu"),
        results_dir=tmp_path,
    )

    # Verify indeterminate cases are tracked under excluded_patients_count
    assert results["excluded_patients_count"] == 1
    assert results["reporting_boundaries"]["multiclass_accuracy_reported"] is False
    assert results["reporting_boundaries"]["specificity_reported"] is False


