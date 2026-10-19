"""
Unit tests for Phase 6 Explanation validation (randomization sanity check, deletion test, gate vs shapley).
"""

import pytest
import torch
import torch.nn as nn

from xmai.explainability.card import ExplanationCard
from xmai.explainability.validation import (
    run_model_randomization_check,
    run_salient_deletion_test,
    compare_gate_and_shapley,
)
from xmai.models.encoders import BModeEncoder
from xmai.models.xmai_model import XMAIModel


def test_model_randomization_sanity_check():
    from xmai.models.track_a_models import A1BModeOnly
    model = A1BModeOnly(pretrained=False)
    img = torch.randn(1, 3, 224, 224)

    res = run_model_randomization_check(model, img, target_class=1)
    assert "spearman_correlation" in res
    assert "sanity_check_passed" in res
    assert isinstance(res["sanity_check_passed"], bool)


def test_salient_deletion_test():
    class DummyModel(nn.Module):
        def forward(self, img=None, clin=None, mod_mask=None):
            # Model output sensitive to mean of image
            val = float(img.mean().item()) if img is not None else 0.0
            p1 = torch.sigmoid(torch.tensor([val]))
            probs = torch.tensor([[1.0 - p1.item(), p1.item()]])
            return {"probs": probs}

    dummy = DummyModel()
    img = torch.ones(1, 3, 224, 224)
    heatmap = torch.zeros(224, 224)
    heatmap[:50, :50] = 1.0  # Top corner salient

    res = run_salient_deletion_test(dummy, img, heatmap, target_class=1, top_fraction=0.10)
    assert "original_probability" in res
    assert "salient_drop" in res
    assert "random_drop" in res


def test_compare_gate_and_shapley():
    model = XMAIModel(pretrained=False)
    img = torch.randn(1, 3, 224, 224)
    clin = torch.randn(1, 2)

    res = compare_gate_and_shapley(model, img, clin, target_class=1)
    assert "gate_weights" in res
    assert "modality_shapley" in res
    assert "agreement" in res
    assert "M1_bmode" in res["gate_weights"]
    assert "M3_context" in res["gate_weights"]


def test_explanation_card_markdown():
    card = ExplanationCard(
        patient_id="SMC_001",
        true_label="HCC",
        pred_label="HCC",
        probs={"HCC": 0.95, "Hemangioma": 0.05},
        margin=0.90,
        gate_weights={"B-mode": 0.70, "CEUS": 0.0, "Context": 0.30},
        shapley_values={"B-mode": +0.40, "CEUS": 0.0, "Context": +0.10},
    )
    md = card.render_markdown()
    assert "Patient SMC_001" in md
    assert "0.9500" in md
    assert "0.9000" in md
