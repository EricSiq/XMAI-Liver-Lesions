"""
Unit tests for CrossModalSpatialAttentionVisualizer.
"""

import numpy as np
import pytest
import torch
from xmai.explainability.cross_attention_viz import CrossModalSpatialAttentionVisualizer
from xmai.models.track_a_models import create_track_a_model


def test_cross_modal_spatial_attention_visualizer():
    # Instantiate A8 Cross-Modal Attention model
    model = create_track_a_model("A8", pretrained=False)
    viz = CrossModalSpatialAttentionVisualizer(model)

    img = torch.randn(1, 3, 224, 224)
    clin = torch.tensor([[1.2, 1.0]])  # Age=75, Male

    out_maps = viz.compute_spatial_clinical_attention(img, clin)

    assert "spatial_attention" in out_maps
    assert "differential_attention" in out_maps

    sp_attn = out_maps["spatial_attention"]
    diff_attn = out_maps["differential_attention"]

    assert sp_attn.shape == (224, 224)
    assert diff_attn.shape == (224, 224)
    assert 0.0 <= sp_attn.min() <= sp_attn.max() <= 1.0
    assert not np.isnan(sp_attn).any()
    assert not np.isnan(diff_attn).any()

    # Test RGB overlay generation
    mock_bmode = np.random.randint(0, 255, (224, 224), dtype=np.uint8)
    blended = viz.generate_clinical_attention_overlay(mock_bmode, sp_attn, alpha=0.4)
    assert blended.shape == (224, 224, 3)
    assert blended.dtype == np.uint8

    viz.remove_hooks()


def test_spatial_neutral_prior_zero_difference():
    """When clinical covariates match the neutral prior (clin=0), differential attention must be identically zero."""
    model = create_track_a_model("A8", pretrained=False)
    viz = CrossModalSpatialAttentionVisualizer(model)

    img = torch.randn(1, 3, 224, 224)
    zero_clin = torch.zeros(1, 2)

    out = viz.compute_spatial_clinical_attention(img, zero_clin)
    diff = out["differential_attention"]

    assert np.allclose(diff, 0.0, atol=1e-5), "Differential attention must be 0 when covariates match neutral prior"
    viz.remove_hooks()


def test_spatial_attention_entropy_bounds():
    """Spatial attention patch distribution must have valid Shannon entropy in [0, log(49)]."""
    model = create_track_a_model("A8", pretrained=False)
    viz = CrossModalSpatialAttentionVisualizer(model)

    img = torch.randn(1, 3, 224, 224)
    clin = torch.tensor([[2.5, 1.0]])

    _ = viz.compute_spatial_clinical_attention(img, clin)
    feats = viz.spatial_features
    energy = torch.norm(feats, p=2, dim=1).squeeze(0)  # [7, 7]
    prob = torch.softmax(energy.view(-1) / 2.0, dim=0).cpu().numpy()

    assert pytest.approx(prob.sum(), abs=1e-5) == 1.0, "Patch probabilities must sum to 1.0"

    entropy = -np.sum(prob * np.log(prob + 1e-12))
    max_entropy = np.log(49.0)  # log(7*7)
    assert 0.0 <= entropy <= max_entropy + 1e-5, f"Entropy {entropy} out of bounds [0, {max_entropy}]"

    viz.remove_hooks()


def test_extreme_clinical_covariates_stability():
    """Extreme clinical covariate values (+/- 50.0 std) must produce finite normalized attention maps."""
    model = create_track_a_model("A4", pretrained=False)
    viz = CrossModalSpatialAttentionVisualizer(model)

    img = torch.randn(1, 3, 224, 224)
    extreme_clin = torch.tensor([[50.0, -50.0]])

    out = viz.compute_spatial_clinical_attention(img, extreme_clin)
    assert np.isfinite(out["spatial_attention"]).all()
    assert np.isfinite(out["differential_attention"]).all()
    assert 0.0 <= out["spatial_attention"].min() <= out["spatial_attention"].max() <= 1.0

    viz.remove_hooks()


def test_overlay_grayscale_and_rgb_resilience():
    """Overlay generator must support both 2D grayscale and 3D RGB inputs of arbitrary resolution."""
    model = create_track_a_model("A8", pretrained=False)
    viz = CrossModalSpatialAttentionVisualizer(model)

    dummy_attn = np.ones((224, 224), dtype=np.float32)

    # 2D grayscale input (300, 400)
    gray = np.full((300, 400), 128, dtype=np.uint8)
    blended_gray = viz.generate_clinical_attention_overlay(gray, dummy_attn)
    assert blended_gray.shape == (300, 400, 3)

    # 3D RGB input (200, 200, 3)
    rgb = np.full((200, 200, 3), 64, dtype=np.uint8)
    blended_rgb = viz.generate_clinical_attention_overlay(rgb, dummy_attn)
    assert blended_rgb.shape == (200, 200, 3)

    viz.remove_hooks()

