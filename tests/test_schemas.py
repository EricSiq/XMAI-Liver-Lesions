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


@pytest.mark.parametrize("prohibited_key", [
    "t_stage", "T_STAGE", "t-stage", "  t_stage  ",
    "tumor_size", "tumor_size_cm", "max_diameter",
    "pathologic_t_stage", "tace_response", "complete_response_to_tace",
    "year", "acquisition_format", "file_size", "frame_count",
])
def test_all_prohibited_leakage_fields_blocked(prohibited_key):
    """Stress test that EVERY forbidden field name in any case or formatting is blocked."""
    with pytest.raises(ValueError, match="LEAKAGE ASSERTION FAILED"):
        assert_no_leakage_fields({prohibited_key: "leaked_value"})


def test_smc_manifest_age_and_fold_boundaries():
    """Verify age boundaries (0-120) and fold boundaries (0-4) are strictly enforced."""
    # Negative age must fail
    with pytest.raises(Exception):
        SMCManifestRow(
            patient_id="P1", subject_id=1, relative_path="p/1.png", label="HCC",
            is_clean=True, age=-5.0, fold=0, image_sha256="abc"
        )
    # Age > 120 must fail
    with pytest.raises(Exception):
        SMCManifestRow(
            patient_id="P2", subject_id=2, relative_path="p/2.png", label="HCC",
            is_clean=True, age=125.0, fold=0, image_sha256="abc"
        )
    # Fold < 0 or > 4 must fail
    with pytest.raises(Exception):
        SMCManifestRow(
            patient_id="P3", subject_id=3, relative_path="p/3.png", label="HCC",
            is_clean=True, age=50.0, fold=5, image_sha256="abc"
        )


def test_clinical_feature_processor_invariants():
    """Verify fold isolation, pre-fit assertion, and imputation behavior."""
    import pandas as pd
    from xmai.data.clinical import ClinicalFeatureProcessor

    proc = ClinicalFeatureProcessor()
    # Calling transform before fit must raise RuntimeError
    with pytest.raises(RuntimeError, match="must be fitted on training fold"):
        proc.transform_row({"age": 55.0, "sex": "M"})

    # Fitting on dataframe containing prohibited columns must raise
    df_leaked = pd.DataFrame({
        "age": [50.0, 60.0],
        "age_missing": [False, False],
        "t_stage": ["T1", "T2"]
    })
    with pytest.raises(ValueError, match="LEAKAGE ASSERTION FAILED"):
        proc.fit(df_leaked)

    # Valid fit on training fold
    df_train = pd.DataFrame({
        "age": [50.0, 60.0, None],
        "age_missing": [False, False, True],
        "sex": ["M", "F", None],
        "sex_missing": [False, False, True]
    })
    proc.fit(df_train)
    assert proc.is_fitted
    assert proc.age_mean == 55.0
    assert proc.age_median == 55.0

    # Transforming missing age and sex must impute training median and 0.5 binary sex
    feat, mask = proc.transform_row({"age": None, "age_missing": True, "sex": None, "sex_missing": True})
    assert feat[0].item() == pytest.approx(0.0)  # (55 - 55) / std == 0
    assert feat[1].item() == 0.5
    assert mask[0].item() == 1.0
    assert mask[1].item() == 1.0


def test_multiclass_schemas_and_taxonomy():
    """Verify 5-class and 6-class schemas, tier validation, and clinical profiles."""
    from xmai.data.schemas import (
        TAXONOMY_5CLASS,
        TAXONOMY_6CLASS,
        CLASS_TIER_MAPPING,
        ClinicalCovariates8,
        MulticlassManifestRow,
    )

    assert len(TAXONOMY_5CLASS) == 5
    assert len(TAXONOMY_6CLASS) == 6
    assert set(TAXONOMY_5CLASS).issubset(set(TAXONOMY_6CLASS))

    # Valid malignant row
    row_hcc = MulticlassManifestRow(
        patient_id="HCC_01",
        relative_path="data/clean/HCC_01.png",
        label="HCC",
        tier="Malignant",
        fold=0,
        data_source="SMC-LUD",
        verification_status="VERIFIED_HISTOPATHOLOGY",
        clinical=ClinicalCovariates8(age=62, sex="M", cirrhosis=1, hepatitis=1, afp_level=240.0),
    )
    assert row_hcc.label == "HCC"
    assert row_hcc.tier == "Malignant"

    # Valid benign row
    row_fnh = MulticlassManifestRow(
        patient_id="FNH_01",
        relative_path="data/clean/FNH_01.png",
        label="FNH",
        tier="Benign",
        fold=1,
        data_source="SYSU-CEUS",
        verification_status="VERIFIED_IMAGING_CONSENSUS",
        clinical=ClinicalCovariates8(age=34, sex="F", oral_contraceptives=1),
    )
    assert row_fnh.label == "FNH"
    assert row_fnh.tier == "Benign"

    # Mismatched tier must raise ValueError
    with pytest.raises(ValueError, match="tier mismatch"):
        MulticlassManifestRow(
            patient_id="ERR_01",
            relative_path="data/clean/ERR_01.png",
            label="Cholangiocarcinoma",
            tier="Benign",  # Error: Cholangiocarcinoma is Malignant!
            fold=2,
            data_source="TCIA",
            verification_status="VERIFIED_HISTOPATHOLOGY",
        )


