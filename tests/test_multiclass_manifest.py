"""
Unit and integration tests for the universal multiclass focal liver lesion manifest.
Verifies label taxonomies, patient isolation across folds, leakage barriers, and clinical distributions.
"""

import pytest
import pandas as pd
from xmai.data.multiclass_manifest import (
    build_multiclass_manifest,
    load_multiclass_manifest,
    get_multiclass_splits,
)
from xmai.data.schemas import (
    TAXONOMY_5CLASS,
    CLASS_TIER_MAPPING,
    assert_no_leakage_fields,
)


@pytest.fixture(scope="module")
def manifest_df():
    """Load or generate the multiclass manifest for tests."""
    return load_multiclass_manifest()


def test_multiclass_manifest_shape_and_classes(manifest_df):
    """Verify that the manifest contains all 5 required classes and valid row counts."""
    assert len(manifest_df) >= 1000
    labels = set(manifest_df["label"].unique())
    assert labels == set(TAXONOMY_5CLASS)

    # Check minimum per-class samples
    for label in TAXONOMY_5CLASS:
        count = (manifest_df["label"] == label).sum()
        assert count >= 150, f"Insufficient samples for class {label}: {count}"


def test_multiclass_tier_consistency(manifest_df):
    """Verify that every row's tier matches the oncologic ground truth mapping."""
    for _, row in manifest_df.iterrows():
        expected_tier = CLASS_TIER_MAPPING[row["label"]]
        assert row["tier"] == expected_tier, f"Tier mismatch for {row['label']}: {row['tier']} != {expected_tier}"


def test_multiclass_patient_isolation_across_all_folds():
    """Verify 100% patient isolation: zero patient overlap between train and test across all 5 folds."""
    for fold in range(5):
        train_df, test_df = get_multiclass_splits(fold)
        train_patients = set(train_df["patient_id"])
        test_patients = set(test_df["patient_id"])

        overlap = train_patients.intersection(test_patients)
        assert len(overlap) == 0, f"CRITICAL LEAKAGE: Fold {fold} has {len(overlap)} overlapping patients: {overlap}"
        assert len(test_patients) > 0
        assert len(train_patients) > len(test_patients)


def test_multiclass_leakage_assertion(manifest_df):
    """Verify that no forbidden leakage fields enter the multiclass manifest."""
    for _, row in manifest_df.iterrows():
        assert_no_leakage_fields(row.to_dict())


def test_multiclass_provenance_and_verification_integrity(manifest_df):
    """Verify data provenance tracking and synthetic status integrity."""
    sources = set(manifest_df["data_source"].unique())
    assert "SMC-LUD" in sources
    assert "WFUMB-Acoustic" in sources

    # Check that SMC-LUD, TCIA, and SYSU cases are flagged non-synthetic
    real_mask = manifest_df["data_source"].isin(["SMC-LUD", "TCIA", "SYSU-CEUS"])
    assert not manifest_df.loc[real_mask, "is_synthetic"].any(), "Real cases must have is_synthetic == False"

    # Check that WFUMB reference cases are marked synthetic
    synth_mask = manifest_df["data_source"] == "WFUMB-Acoustic"
    assert manifest_df.loc[synth_mask, "is_synthetic"].all(), "Reference cases must have is_synthetic == True"


def test_multiclass_clinical_demographic_patterns(manifest_df):
    """Verify that clinical covariates adhere to real-world oncology epidemiology."""
    hcc_df = manifest_df[manifest_df["label"] == "HCC"]
    fnh_df = manifest_df[manifest_df["label"] == "FNH"]

    # HCC has male predominance
    hcc_male_ratio = (hcc_df["sex"] == "M").mean()
    assert hcc_male_ratio > 0.60, f"HCC expected male predominance, got {hcc_male_ratio}"

    # FNH has female predominance and younger age
    fnh_female_ratio = (fnh_df["sex"] == "F").mean()
    assert fnh_female_ratio > 0.70, f"FNH expected female predominance, got {fnh_female_ratio}"
    assert fnh_df["age"].mean() < hcc_df["age"].mean()
