"""
Unit tests for modality encoders, gated fusion, and XMAIModel forward passes.
"""

import pytest
import torch

from xmai.models.encoders import BModeEncoder, ClinicalEncoder
from xmai.models.fusion import MaskAwareGatedFusion
from xmai.models.xmai_model import XMAIModel


def test_bmode_encoder():
    model = BModeEncoder(pretrained=False, embed_dim=256)
    x = torch.randn(2, 3, 224, 224)
    z_b = model(x)

    assert z_b.shape == (2, 256)
    assert model.last_features is not None
    assert model.last_features.shape == (2, 512, 7, 7)


def test_clinical_encoder():
    model = ClinicalEncoder(in_features=2, hidden_dim=64, out_dim=64)
    clin = torch.randn(4, 2)
    z_t = model(clin)
    assert z_t.shape == (4, 64)


def test_mask_aware_gated_fusion():
    fusion = MaskAwareGatedFusion(dim_b=256, dim_c=256, dim_t=64, fused_dim=256, dropout_p=0.0)
    fusion.eval()

    z_b = torch.randn(3, 256)
    z_t = torch.randn(3, 64)
    # Mask: M1 present, M2 absent, M3 present
    mod_mask = torch.tensor([[1.0, 0.0, 1.0]] * 3)

    z_f, gate_weights = fusion(z_b=z_b, z_c=None, z_t=z_t, mod_mask=mod_mask)

    assert z_f.shape == (3, 256)
    assert gate_weights.shape == (3, 3)
    # M2 should have 0.0 gate weight
    assert (gate_weights[:, 1] < 1e-6).all()
    # Weights should sum to 1.0
    assert torch.allclose(gate_weights.sum(dim=-1), torch.ones(3), atol=1e-5)


def test_xmai_model_multimodal():
    model = XMAIModel(num_classes=2, pretrained=False, dim_b=256, dim_t=64, fused_dim=256, dropout_p=0.0)
    model.eval()

    img = torch.randn(2, 3, 224, 224)
    clin = torch.randn(2, 2)
    mod_mask = torch.tensor([[1.0, 0.0, 1.0], [1.0, 0.0, 1.0]])

    out = model(img=img, clin=clin, mod_mask=mod_mask)

    assert "logits" in out
    assert "probs" in out
    assert "gate_weights" in out
    assert out["logits"].shape == (2, 2)
    assert out["probs"].shape == (2, 2)
    # Probabilities must sum to 1.0
    assert torch.allclose(out["probs"].sum(dim=-1), torch.ones(2), atol=1e-5)


def test_temperature_scaling():
    model = XMAIModel(num_classes=2, pretrained=False)
    img = torch.randn(2, 3, 224, 224)
    clin = torch.randn(2, 2)

    model.set_temperature(2.0)
    out = model(img=img, clin=clin)

    assert torch.allclose(out["calibrated_logits"], out["logits"] / 2.0)
