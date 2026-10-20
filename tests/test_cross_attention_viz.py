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
