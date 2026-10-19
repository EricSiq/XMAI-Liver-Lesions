"""
Tests for Pydantic data schemas and leakage assertions.
"""

import pytest
from xmai.data.schemas import (
    AULManifestRow,
    PredictionRow,
    SMCManifestRow,
    SYSUManifestRow,
    TCIAManifestRow,
    assert_no_leakage_fields,
)


def test_smc_manifest_row_valid():
    row = SMCManifestRow(
        patient_id="HCC_2",
        subject_id=2,
        relative_path="SMC-LUD Liver Ultrasound Dataset (HCC vs Hemangioma)/original_data/HCC/HCC_clean (wo caliper)/HCC_2/image_0.png",
        label="HCC",
        is_clean=True,
        age=80.0,
        age_missing=False,
        sex="M",
        sex_missing=False,
        fold=0,
        image_sha256="abcdef1234567890",
    )
    assert row.patient_id == "HCC_2"
    assert row.label == "HCC"
    assert row.age == 80.0


def test_smc_manifest_row_invalid_label():
    with pytest.raises(Exception):
        SMCManifestRow(
            patient_id="HCC_2",
            subject_id=2,
            relative_path="path/to/img.png",
            label="Cyst",  # Invalid! Not in SMC label space
            is_clean=True,
            age=65.0,
            fold=1,
            image_sha256="abc",
        )


def test_smc_manifest_row_rejects_unclean():
    with pytest.raises(Exception):
        SMCManifestRow(
            patient_id="HCC_2",
            subject_id=2,
            relative_path="path/to/caliper.png",
            label="HCC",
            is_clean=False,  # Prohibited!
            age=65.0,
            fold=1,
            image_sha256="abc",
        )


def test_prediction_row_valid():
    row = PredictionRow(
        patient_id="HCC_2",
        track="A",
        fold=0,
        seed=42,
        model_id="A4_gated_fusion",
        true_label="HCC",
        pred_label="HCC",
        prob_vector={"HCC": 0.85, "Hemangioma": 0.15},
        margin=0.70,
        is_calibrated=True,
        is_low_margin=False,
        is_error=False,
        modality_mask=[1, 0, 1],
    )
    assert row.pred_label == "HCC"
    assert sum(row.prob_vector.values()) == pytest.approx(1.0)


def test_prediction_row_rejects_unnormalized_probabilities():
    with pytest.raises(ValueError):
        PredictionRow(
            patient_id="HCC_2",
            track="A",
            fold=0,
            seed=42,
            model_id="A4_gated_fusion",
            true_label="HCC",
            pred_label="HCC",
            prob_vector={"HCC": 0.85, "Hemangioma": 0.85},  # Sums to 1.7!
            margin=0.0,
            is_calibrated=True,
            is_low_margin=False,
            is_error=False,
            modality_mask=[1, 0, 1],
        )

    # Test NaN probability rejection
    with pytest.raises(ValueError):
        PredictionRow(
            patient_id="HCC_NaN",
            track="A",
            fold=0,
            seed=42,
            model_id="A4_gated_fusion",
            true_label="HCC",
            pred_label="HCC",
            prob_vector={"HCC": float("nan"), "Hemangioma": float("nan")},
            margin=0.0,
            is_calibrated=True,
            is_low_margin=False,
            is_error=False,
            modality_mask=[1, 0, 1],
        )


def test_leakage_assertion():
    # Clean features: must pass
    clean_features = {"age": 65, "sex": "M", "age_missing": 0}
    assert_no_leakage_fields(clean_features)

    # Prohibited features: must raise ValueError
    with pytest.raises(ValueError, match="LEAKAGE ASSERTION FAILED"):
        assert_no_leakage_fields({"age": 65, "tumor_size": "3.2 cm"})

    with pytest.raises(ValueError, match="LEAKAGE ASSERTION FAILED"):
        assert_no_leakage_fields({"age": 65, "pathologic_t_stage": "pT2"})

    with pytest.raises(ValueError, match="LEAKAGE ASSERTION FAILED"):
        assert_no_leakage_fields({"age": 65, "tace_response": "Complete"})
