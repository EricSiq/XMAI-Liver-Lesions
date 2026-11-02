import pytest
from scripts.serve_frontend import (
    compute_live_multiclass_prediction,
    MULTICLASS_5CLASS_TAXONOMY,
    MULTICLASS_5CLASS_CASES,
)


def test_5class_taxonomy_schema():
    assert len(MULTICLASS_5CLASS_TAXONOMY) == 5
    expected_labels = ["HCC", "Hemangioma", "FNH", "Adenoma", "Cholangiocarcinoma"]
    for i, cls in enumerate(MULTICLASS_5CLASS_TAXONOMY):
        assert cls["label"] == expected_labels[i]
        assert "tier" in cls
        assert "is_malignant" in cls
        assert "ultrasound_phenotype" in cls
        assert "epidemiological_triad" in cls


def test_5class_case_fixtures():
    assert len(MULTICLASS_5CLASS_CASES) == 5
    for case in MULTICLASS_5CLASS_CASES:
        assert "patient_id" in case
        assert "true_label" in case
        assert len(case["visual_priors"]) == 5
        assert 0.99 <= sum(case["visual_priors"]) <= 1.01


def test_live_multiclass_prediction_architectures():
    models = ["M5_gated", "M5_hierarchical", "M5_evidential"]
    for model_id in models:
        res = compute_live_multiclass_prediction(
            model_id=model_id,
            age=67,
            sex="Male",
            cirrhosis=1,
            hepatitis=1,
            afp_elevated=1,
            ca19_9_elevated=0,
            ocp_use=0,
            lesion_size_cm=4.5,
            mask=1,
            visual_priors=[0.4, 0.2, 0.15, 0.15, 0.1],
        )
        assert res["status"] == "success"
        assert res["fallback_active"] is False
        assert len(res["probabilities"]) == 5
        assert pytest.approx(sum(res["probabilities"].values()), abs=1e-3) == 1.0
        assert res["top1_class"] == "HCC"
        assert res["is_malignant"] is True

        # Invariant for evidential belief decomposition
        beliefs = res["evidential"]["beliefs"]
        uncertainty = res["evidential"]["uncertainty"]
        assert pytest.approx(sum(beliefs.values()) + uncertainty, abs=1e-2) == 1.0


def test_live_multiclass_h3_fallback():
    res = compute_live_multiclass_prediction(
        model_id="M5_gated",
        age=67,
        sex="Male",
        cirrhosis=1,
        hepatitis=1,
        afp_elevated=1,
        ca19_9_elevated=0,
        ocp_use=0,
        lesion_size_cm=4.5,
        mask=0,
        visual_priors=[0.1, 0.7, 0.1, 0.05, 0.05],
    )
    assert res["status"] == "success"
    assert res["fallback_active"] is True
    assert res["gate_b"] == 1.0
    assert res["gate_c"] == 0.0
    assert res["top1_class"] == "Hemangioma"
    assert res["is_malignant"] is False
