"""
Unit tests for Grad-CAM, exact Modality Shapley, and Explanation Cards.
"""

import numpy as np
import pytest
import torch

from xmai.explainability.card import ExplanationCard
from xmai.explainability.gradcam import GradCAM
from xmai.explainability.modality_shapley import compute_exact_modality_shapley
from xmai.models.xmai_model import XMAIModel


def test_gradcam():
    model = XMAIModel(num_classes=2, pretrained=False)
    gradcam = GradCAM(model, model.encoder_b.layer4)

    img = torch.randn(1, 3, 224, 224, requires_grad=True)
    clin = torch.randn(1, 2)
    mod_mask = torch.tensor([[1.0, 0.0, 1.0]])

    heatmap = gradcam.generate_heatmap(img, target_class=1, clin_tensor=clin, mod_mask=mod_mask)
    gradcam.remove_hooks()

    assert isinstance(heatmap, np.ndarray)
    assert heatmap.shape == (224, 224)
    assert 0.0 <= heatmap.min()
    assert heatmap.max() <= 1.0


def test_exact_modality_shapley():
    model = XMAIModel(num_classes=2, pretrained=False)
    img = torch.randn(1, 3, 224, 224)
    clin = torch.randn(1, 2)

    shapley_vals = compute_exact_modality_shapley(model, img=img, clin=clin, ceus=None, target_class=1)

    assert "B-mode" in shapley_vals
    assert "CEUS" in shapley_vals
    assert "Context" in shapley_vals
    for k, v in shapley_vals.items():
        assert -1.0 <= v <= 1.0


def test_explanation_card():
    card = ExplanationCard(
        patient_id="HCC_2",
        true_label="HCC",
        pred_label="HCC",
        probs={"Hemangioma": 0.12, "HCC": 0.88},
        margin=0.76,
        gate_weights={"B-mode": 0.70, "CEUS": 0.0, "Context": 0.30},
        shapley_values={"B-mode": 0.35, "CEUS": 0.0, "Context": 0.15},
        flags=["CohortPriorNotice"],
    )

    d = card.to_dict()
    assert d["patient_id"] == "HCC_2"
    assert d["top2_margin"] == 0.76

    md = card.render_markdown()
    assert "XMAI Explanation Card: Patient HCC_2" in md
    assert "0.8800" in md
