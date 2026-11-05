"""
Unit and stress tests for the 5-class explainability engine:
- MulticlassGradCAM target class localization
- MulticlassKernelSHAP additive efficiency axiom
- Pentagonal explanation dossier generation and certified referral triage
"""

import pytest
import numpy as np
import torch
from xmai.explainability.multiclass_xai import (
    MulticlassGradCAM,
    MulticlassKernelSHAP,
    build_multiclass_dossier,
)
from xmai.models.multiclass_models import M5FlatGatedFusion
from xmai.data.schemas import TAXONOMY_5CLASS


@pytest.fixture(scope="module")
def model_5class():
    """Create lightweight non-pretrained model for fast testing."""
    model = M5FlatGatedFusion(num_classes=5, pretrained=False)
    model.eval()
    return model


def test_multiclass_gradcam_shape_and_bounds(model_5class):
    """Verify Grad-CAM returns normalized [0, 1] heatmaps of resolution 224x224."""
    cam = MulticlassGradCAM(model=model_5class)

    img = torch.randn(1, 3, 224, 224)
    clin = torch.randn(1, 8)

    # Test class 0 (HCC)
    heatmap_hcc = cam.generate_heatmap(img=img, clin=clin, target_class=0)
    assert heatmap_hcc.shape == (224, 224)
    assert 0.0 <= np.min(heatmap_hcc)
    assert np.max(heatmap_hcc) <= 1.0

    # Test class 2 (FNH)
    heatmap_fnh = cam.generate_heatmap(img=img, clin=clin, target_class=2)
    assert heatmap_fnh.shape == (224, 224)
    assert np.max(heatmap_fnh) <= 1.0


def test_multiclass_kernel_shap_additive_efficiency(model_5class):
    """Verify that Shapley attributions satisfy the game-theoretic additive efficiency axiom."""
    shap_engine = MulticlassKernelSHAP(model=model_5class, num_classes=5)

    img = torch.randn(1, 3, 224, 224)
    clin = torch.tensor([[65.0, 1.0, 1.0, 1.0, 0.0, 1.0, 4.5, 2.8]])  # High risk male

    attributions = shap_engine.explain(img=img, clin=clin)

    assert len(attributions) == 5
    for c_name in TAXONOMY_5CLASS:
        assert c_name in attributions
        c_dict = attributions[c_name]
        # Sum of phi_i must approximately equal total_logit - base_logit
        total_logit = c_dict["_total_logit"]
        base_logit = c_dict["_base_logit"]
        phi_sum = sum(v for k, v in c_dict.items() if not k.startswith("_"))

        expected_shift = total_logit - base_logit
        assert phi_sum == pytest.approx(expected_shift, abs=1e-3), (
            f"Additivity axiom failed for {c_name}: {phi_sum} != {expected_shift}"
        )


def test_build_multiclass_dossier_referral_logic():
    """Verify clinical triage referral triggers on high uncertainty or low acoustic margin."""
    # Scenario A: Highly confident, low uncertainty -> Autonomous triage
    probs_confident = {"HCC": 0.88, "Cholangiocarcinoma": 0.05, "Hemangioma": 0.03, "FNH": 0.02, "Adenoma": 0.02}
    dossier_a = build_multiclass_dossier(
        patient_id="PT_OK",
        true_label="HCC",
        pred_label="HCC",
        probs=probs_confident,
        uncertainty=0.08,
        shap_attributions={"Cirrhosis": 1.2, "Age": 0.5},
    )
    assert not dossier_a["certified_referral_flag"]
    assert "Autonomous confident triage certified" in dossier_a["referral_rationale"]

    # Scenario B: High uncertainty (u > 0.25) -> Must flag referral
    dossier_b = build_multiclass_dossier(
        patient_id="PT_UNCERTAIN",
        true_label="FNH",
        pred_label="Adenoma",
        probs={"Adenoma": 0.35, "FNH": 0.30, "Hemangioma": 0.20, "HCC": 0.10, "Cholangiocarcinoma": 0.05},
        uncertainty=0.32,  # > 0.25
        shap_attributions={"Oral Contraceptives": 1.1},
    )
    assert dossier_b["certified_referral_flag"]
    assert "Elevated epistemic uncertainty" in dossier_b["referral_rationale"]

    # Scenario C: Low acoustic margin (< 0.15) between top-2 -> Must flag referral
    dossier_c = build_multiclass_dossier(
        patient_id="PT_BORDERLINE",
        true_label="Cholangiocarcinoma",
        pred_label="HCC",
        probs={"HCC": 0.42, "Cholangiocarcinoma": 0.38, "Hemangioma": 0.10, "FNH": 0.05, "Adenoma": 0.05},
        uncertainty=0.12,  # low uncertainty, but margin is 0.04 < 0.15
        shap_attributions={"Age": 0.4},
    )
    assert dossier_c["certified_referral_flag"]
    assert "Borderline acoustic margin" in dossier_c["referral_rationale"]


def test_multiclass_gradcam_context_manager_lifecycle(model_5class):
    """Verify MulticlassGradCAM context manager cleans up hooks cleanly."""
    with MulticlassGradCAM(model=model_5class) as cam:
        img = torch.randn(1, 3, 224, 224)
        hm = cam.generate_heatmap(img=img, target_class=1)
        assert hm.shape == (224, 224)
    # After exit, hooks should be removed
    assert cam.forward_handle is None
    assert cam.backward_handle is None

