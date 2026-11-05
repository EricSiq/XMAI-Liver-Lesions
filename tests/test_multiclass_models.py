"""
Comprehensive unit and stress tests for the 5-class / 6-class multimodal models:
- M5FlatGatedFusion
- M5HierarchicalFusion
- M5EvidentialFusion
Verifies output dimensions, gradient flow, mathematical normalization, and temperature calibration.
"""

import pytest
import torch
from xmai.models.multiclass_models import (
    M5FlatGatedFusion,
    M5HierarchicalFusion,
    M5EvidentialFusion,
)
from xmai.data.schemas import TAXONOMY_5CLASS


@pytest.mark.parametrize("num_classes", [5, 6])
def test_m5_flat_gated_fusion_forward_and_gradients(num_classes):
    """Verify M5FlatGatedFusion forward pass, probability normalization, and backprop."""
    class_names = TAXONOMY_5CLASS if num_classes == 5 else TAXONOMY_5CLASS + ["Cyst"]
    model = M5FlatGatedFusion(num_classes=num_classes, pretrained=False, class_names=class_names)
    model.train()

    B = 4
    img = torch.randn(B, 3, 224, 224, requires_grad=True)
    clin = torch.randn(B, 8, requires_grad=True)
    mask = torch.tensor([[1.0, 1.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])

    out = model(img=img, clin=clin, mod_mask=mask)
    assert out["probs"].shape == (B, num_classes)
    assert out["logits"].shape == (B, num_classes)
    assert out["gate_weights"].shape == (B, 2)

    # Check probabilities sum to 1.0
    prob_sums = out["probs"].sum(dim=-1)
    assert torch.allclose(prob_sums, torch.ones_like(prob_sums), atol=1e-5)

    # Backprop verification
    loss = out["probs"].sum()
    loss.backward()
    assert img.grad is not None
    assert clin.grad is not None

    # Test temperature scaling
    model.set_temperature(1.5)
    assert model.temperature.item() == 1.5


def test_m5_hierarchical_fusion_law_of_total_probability():
    """Verify M5HierarchicalFusion coarse-to-fine structure and mathematical consistency."""
    model = M5HierarchicalFusion(num_classes=5, pretrained=False)
    model.eval()

    B = 8
    img = torch.randn(B, 3, 224, 224)
    clin = torch.randn(B, 8)

    out = model(img=img, clin=clin)

    # 1. Total probability across 5 classes must sum to 1.0
    prob_sums = out["probs"].sum(dim=-1)
    assert torch.allclose(prob_sums, torch.ones_like(prob_sums), atol=1e-5)

    # 2. Stage 1 probabilities (p_mal + p_ben) must sum to 1.0
    stage1_sums = (out["p_malignant"] + out["p_benign"]).squeeze(-1)
    assert torch.allclose(stage1_sums, torch.ones_like(stage1_sums), atol=1e-5)

    # 3. Setting temperatures
    model.set_temperatures(t_stage1=1.2, t_ben=1.3, t_mal=1.4)
    assert model.temp_stage1.item() == pytest.approx(1.2)
    assert model.temp_ben.item() == pytest.approx(1.3)
    assert model.temp_mal.item() == pytest.approx(1.4)


def test_m5_evidential_fusion_dempster_shafer_invariants():
    """Verify M5EvidentialFusion Subjective Logic belief and uncertainty decomposition."""
    model = M5EvidentialFusion(num_classes=5, pretrained=False)
    model.eval()

    B = 6
    img = torch.randn(B, 3, 224, 224)
    clin = torch.randn(B, 8)
    out = model(img=img, clin=clin)

    b_fused = out["b_fused"]
    u_fused = out["u_fused"]
    probs = out["probs"]

    # Invariant: sum_{k=1}^K b_k + u == 1.0
    total_belief = b_fused.sum(dim=-1, keepdim=True) + u_fused
    assert torch.allclose(total_belief, torch.ones_like(total_belief), atol=1e-5)

    # Invariant: Expected probs sum to 1.0
    prob_sums = probs.sum(dim=-1)
    assert torch.allclose(prob_sums, torch.ones_like(prob_sums), atol=1e-5)

    # All beliefs and uncertainties must be strictly non-negative and <= 1.0
    assert torch.all(b_fused >= 0.0) and torch.all(b_fused <= 1.0)
    assert torch.all(u_fused >= 0.0) and torch.all(u_fused <= 1.0)

