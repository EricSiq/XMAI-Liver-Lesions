"""
Unit and integration tests for SMC-LUD manifest generation, metadata join, and patient-level folds.
"""

from pathlib import Path
import pandas as pd
import pytest

from xmai.data.schemas import SMCManifestRow
from xmai.data.smc_manifest import generate_smc_manifest, load_and_clean_metadata


@pytest.fixture
def workspace_root():
    return Path(__file__).parent.parent


def test_load_and_clean_metadata(workspace_root):
    smc_root = workspace_root / "SMC-LUD Liver Ultrasound Dataset (HCC vs Hemangioma)"
    meta = load_and_clean_metadata(smc_root)
    assert len(meta) > 700

    # Spot check HCC_2
    assert "HCC_2" in meta
    assert meta["HCC_2"]["label"] == "HCC"
    assert meta["HCC_2"]["subject_id"] == 2
    assert meta["HCC_2"]["sex"] == "M"

    # Spot check Hem_10
    assert "Hem_10" in meta
    assert meta["Hem_10"]["label"] == "Hemangioma"
    assert meta["Hem_10"]["sex"] in {"M", "F"}


def test_generate_smc_manifest_patient_exclusivity(workspace_root, tmp_path):
    output_csv = tmp_path / "test_smc_manifest.csv"
    manifest_df, audit_stats = generate_smc_manifest(
        workspace_root=workspace_root,
        output_manifest_path=output_csv,
        seed=42,
    )

    assert output_csv.exists()
    assert len(manifest_df) > 2000

    # 1. Check patient exclusivity across folds
    patient_folds = manifest_df.groupby("patient_id")["fold"].nunique()
    assert (patient_folds == 1).all(), "CRITICAL: Patient leakage detected! Some patients appear in multiple folds."

    # 2. Check that all 5 folds exist and have both classes
    for fold_idx in range(5):
        fold_df = manifest_df[manifest_df["fold"] == fold_idx]
        assert len(fold_df[fold_df["label"] == "HCC"]) > 0
        assert len(fold_df[fold_df["label"] == "Hemangioma"]) > 0

    # 3. Check schema compliance of all rows
    for _, row in manifest_df.iterrows():
        SMCManifestRow(**row.to_dict())

    # 4. Check unmatched folders (Hem_87)
    assert "Hem_87" in audit_stats["unmatched_folders"]
    assert "Hem_87" not in manifest_df["patient_id"].values


def test_manifest_determinism(workspace_root, tmp_path):
    out1 = tmp_path / "manifest_seed42_a.csv"
    out2 = tmp_path / "manifest_seed42_b.csv"

    df1, _ = generate_smc_manifest(workspace_root, out1, seed=42)
    df2, _ = generate_smc_manifest(workspace_root, out2, seed=42)

    pd.testing.assert_frame_equal(df1, df2)


def test_pairwise_fold_patient_disjointness(workspace_root, tmp_path):
    """Stress test that every pair of folds has strictly zero shared patients (pairwise disjointness)."""
    out_csv = tmp_path / "disjoint_test.csv"
    manifest_df, _ = generate_smc_manifest(workspace_root, out_csv, seed=42)

    folds = sorted(manifest_df["fold"].unique())
    assert len(folds) == 5

    patient_sets = {f: set(manifest_df[manifest_df["fold"] == f]["patient_id"]) for f in folds}

    for i in range(len(folds)):
        for j in range(i + 1, len(folds)):
            intersection = patient_sets[folds[i]].intersection(patient_sets[folds[j]])
            assert len(intersection) == 0, (
                f"LEAKAGE VIOLATION: Folds {folds[i]} and {folds[j]} share patients: {intersection}"
            )


def test_sha256_hash_digest_integrity(workspace_root, tmp_path):
    """Verify all image SHA-256 digests in manifest are valid 64-char hexadecimal hashes."""
    import re
    out_csv = tmp_path / "sha_test.csv"
    manifest_df, _ = generate_smc_manifest(workspace_root, out_csv, seed=42)

    hex_pattern = re.compile(r"^[a-f0-9]{64}$")
    for sha in manifest_df["image_sha256"]:
        assert hex_pattern.match(sha), f"Malformed SHA-256 digest found: {sha}"


def test_stratified_fold_homogeneity(workspace_root, tmp_path):
    """Verify each fold contains approximately 20% of cohort and maintains class ratio."""
    out_csv = tmp_path / "strata_test.csv"
    manifest_df, _ = generate_smc_manifest(workspace_root, out_csv, seed=42)

    unique_patients = manifest_df.drop_duplicates(subset=["patient_id"])
    total_patients = len(unique_patients)
    cohort_hcc_ratio = (unique_patients["label"] == "HCC").mean()

    for fold_idx in range(5):
        fold_patients = unique_patients[unique_patients["fold"] == fold_idx]
        fold_size = len(fold_patients)
        # Each fold should be ~20% +/- 4%
        assert 0.16 * total_patients <= fold_size <= 0.24 * total_patients

        fold_hcc_ratio = (fold_patients["label"] == "HCC").mean()
        # HCC ratio should match cohort within 5%
        assert abs(fold_hcc_ratio - cohort_hcc_ratio) < 0.06


def test_zero_caliper_leakage_barrier(workspace_root, tmp_path):
    """Verify strictly 0% caliper (annotated) images leak into the modeling manifest."""
    out_csv = tmp_path / "caliper_test.csv"
    manifest_df, _ = generate_smc_manifest(workspace_root, out_csv, seed=42)

    for path in manifest_df["relative_path"]:
        assert "with caliper" not in path.lower(), f"Forbidden caliper image found in manifest: {path}"
        assert "wo caliper" in path.lower() or "clean" in path.lower()

